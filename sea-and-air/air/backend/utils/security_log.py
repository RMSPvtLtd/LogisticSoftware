"""Security event logging.

One place that decides what a security-relevant event looks like, so the
format is consistent and the "never log this" rule is enforced in a single
function rather than remembered at each call site.

Never logged: passwords, password hashes, bearer tokens, JWT contents,
session secrets, or full financial records. Identifiers (username, entity
id, client IP) and the outcome are logged -- that's what makes an incident
reconstructable without turning the log itself into a credential store.

Emitted on the dedicated `raaziq.security` logger so a deployment can route
these to a separate, more protected sink than ordinary application logs.
"""

import logging

logger = logging.getLogger("raaziq.security")


def _emit(level: int, event: str, **fields: object) -> None:
    detail = " ".join(f"{key}={value!r}" for key, value in sorted(fields.items()) if value is not None)
    logger.log(level, "security event=%s %s", event, detail)


def auth_success(*, surface: str, username: str, ip: str) -> None:
    _emit(logging.INFO, "auth.success", surface=surface, username=username, ip=ip)


def auth_failure(*, surface: str, username: str, ip: str, reason: str) -> None:
    _emit(logging.WARNING, "auth.failure", surface=surface, username=username, ip=ip, reason=reason)


def auth_lockout(*, surface: str, username: str, ip: str) -> None:
    _emit(logging.WARNING, "auth.lockout", surface=surface, username=username, ip=ip)


def password_changed(*, surface: str, username: str, ip: str) -> None:
    _emit(logging.WARNING, "auth.password_changed", surface=surface, username=username, ip=ip)


def authorization_denied(*, surface: str, actor: str, resource: str, ip: str) -> None:
    """An authenticated principal was refused access to something. Repeated
    entries here are the signal for enumeration/IDOR probing."""
    _emit(logging.WARNING, "authz.denied", surface=surface, actor=actor, resource=resource, ip=ip)


def unhandled_error(*, path: str, method: str, error_id: str, exc: BaseException) -> None:
    """Full technical detail stays server-side; the client only ever gets
    `error_id` so a report can be correlated to this entry."""
    logger.exception(
        "security event=error.unhandled error_id=%r method=%r path=%r", error_id, method, path, exc_info=exc
    )
