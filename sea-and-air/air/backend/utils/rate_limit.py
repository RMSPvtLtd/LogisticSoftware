"""Failed-login throttling for the three login surfaces (ops, worker,
customer).

Deliberately an in-process, in-memory counter rather than a Redis/database
one. That is a real limitation worth stating plainly: on a multi-instance
deployment (this app runs on Vercel serverless, where each cold start is a
fresh process) the counter is per-instance, so a determined attacker
spraying across instances gets more attempts than the configured maximum.
It still removes the cheap, high-volume case -- a single client hammering
one endpoint -- at zero infrastructure cost. A shared store is the correct
upgrade when one is available; see the security report.

Keyed on (surface, username, client IP) so that:
  - locking is scoped to one account from one source, so an attacker cannot
    lock a legitimate user out of their own account by guessing at it
    (which a username-only key would allow), and
  - one IP spraying many usernames still trips a limit per account.

Only *failed* attempts count. A success clears the counter, so normal use --
including a user mistyping a password a few times -- is never affected.
"""

import time
from dataclasses import dataclass, field

from fastapi import Request

from config import get_settings
from utils.errors import TooManyAttempts


@dataclass
class _Bucket:
    failures: int = 0
    first_failure_at: float = field(default_factory=time.monotonic)


# Module-level: one bucket store per process.
_buckets: dict[tuple[str, str, str], _Bucket] = {}

# The bucket key includes an attacker-controlled username, so without a cap
# an attacker could spray unique usernames and grow this dict without bound
# until the process runs out of memory. Bounded + evicted oldest-first.
# Sized well above any plausible number of concurrently-failing real logins,
# so legitimate users are never evicted in practice.
MAX_TRACKED_BUCKETS = 10_000


def _evict_if_oversized() -> None:
    if len(_buckets) < MAX_TRACKED_BUCKETS:
        return
    # Drop expired entries first; only if that isn't enough, drop the oldest.
    settings = get_settings()
    now = time.monotonic()
    for key, bucket in list(_buckets.items()):
        if now - bucket.first_failure_at >= settings.login_lockout_seconds:
            _buckets.pop(key, None)

    while len(_buckets) >= MAX_TRACKED_BUCKETS:
        oldest = min(_buckets, key=lambda k: _buckets[k].first_failure_at)
        _buckets.pop(oldest, None)


def client_ip(request: Request) -> str:
    """Best-effort client address, used *only* as a throttling bucket key --
    never for authentication or authorization.

    `X-Forwarded-For`'s first entry is preferred because this deploys behind
    Vercel's edge, where `request.client` is always the proxy: keying on it
    would put every user worldwide in one bucket, so a single attacker could
    lock out the entire company. Vercel overwrites this header at the edge
    rather than appending to a client-supplied one, so on that deployment it
    reflects the true caller.

    Behind a proxy that does *not* overwrite it, a caller could rotate the
    header to get a fresh bucket each request. That is an accepted limit of
    IP-based throttling (rotating real source addresses defeats it equally);
    it is called out in the security report rather than papered over. The
    per-account half of the key still applies regardless.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _key(surface: str, username: str, ip: str) -> tuple[str, str, str]:
    return (surface, username.strip().lower(), ip)


def check_not_locked_out(surface: str, username: str, request: Request) -> None:
    """Raise TooManyAttempts if this (account, source) has already exceeded
    the failure budget within the lockout window. Call before verifying a
    password so a locked-out caller never reaches the hashing work."""
    settings = get_settings()
    bucket = _buckets.get(_key(surface, username, client_ip(request)))
    if bucket is None:
        return

    if time.monotonic() - bucket.first_failure_at >= settings.login_lockout_seconds:
        # Window elapsed -- the bucket is stale, treat it as clean.
        _buckets.pop(_key(surface, username, client_ip(request)), None)
        return

    if bucket.failures >= settings.login_max_attempts:
        raise TooManyAttempts("Too many failed sign-in attempts. Please wait and try again.")


def record_failure(surface: str, username: str, request: Request) -> None:
    settings = get_settings()
    key = _key(surface, username, client_ip(request))
    bucket = _buckets.get(key)
    now = time.monotonic()

    if bucket is None or now - bucket.first_failure_at >= settings.login_lockout_seconds:
        _evict_if_oversized()
        _buckets[key] = _Bucket(failures=1, first_failure_at=now)
        return

    bucket.failures += 1


def record_success(surface: str, username: str, request: Request) -> None:
    _buckets.pop(_key(surface, username, client_ip(request)), None)


def reset() -> None:
    """Clears all buckets. For test isolation only."""
    _buckets.clear()
