"""The one place that decides which provider answers a tracking request.
Everything above this (the API route, eventually the frontend) calls
`track_container(container_number)` and gets back a normalized
`TrackingResult` -- it has no idea SAPT specifically is behind it, which is
exactly what lets a second provider be added here later without touching
the API layer or the frontend at all.

There's currently exactly one provider (SAPT) and no per-container routing
logic to speak of, but the seam is real: `_PROVIDERS` is where a future
KICT/QICT/shipping-line/customs connector gets registered, and
`track_container` is where the (currently trivial) "which provider handles
this container" decision would grow if terminals ever needed to be told
apart by container prefix, requested terminal, or some other signal.
"""

from integrations.tracking.protocol import TrackingProvider
from integrations.tracking.sapt import SAPTProvider
from schemas.tracking import TrackingResult

_PROVIDERS: list[TrackingProvider] = [SAPTProvider()]


def track_container(container_number: str) -> TrackingResult:
    """Looks up `container_number`, which the caller (the API route) has
    already validated and normalized via `utils.validation` -- that's the
    "Validate container" step in the tracking flow, and it happens once,
    before this is called, not here.
    """
    provider = _PROVIDERS[0]
    return provider.get_container_history(container_number)
