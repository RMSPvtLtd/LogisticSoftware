"""A fake tracking provider for local development and tests. Stands in for a
real integration (ShipsGo, a carrier API, ...), which is explicitly out of
scope for this MVP. A future real adapter implements the same `get_status`
contract and does its own provider-specific normalization internally.
"""

from datetime import datetime, timezone

from app.adapters.tracking import NormalizedStatus
from app.models.enums import ShipmentStage

_DEFAULT_CANNED_STATUSES: dict[str, NormalizedStatus] = {
    "ABC123": NormalizedStatus(
        stage=ShipmentStage.DEPARTURE,
        occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        note="Flight departed origin airport",
        provider_reference="ABC123",
    ),
    "MSKU7654321": NormalizedStatus(
        stage=ShipmentStage.DEPARTURE,
        occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        note="Vessel departed origin port",
        provider_reference="MSKU7654321",
    ),
}


class MockTrackingAdapter:
    def __init__(self, canned_statuses: dict[str, NormalizedStatus] | None = None):
        self._canned_statuses = canned_statuses if canned_statuses is not None else _DEFAULT_CANNED_STATUSES

    def get_status(self, reference: str) -> NormalizedStatus | None:
        return self._canned_statuses.get(reference)
