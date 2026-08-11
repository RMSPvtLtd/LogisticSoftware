"""The boundary between the outside world (a carrier or tracking provider)
and Raaziq's internal shipment model. This module knows nothing about
Shipment, StatusEvent, or the transition service — it only defines what a
provider integration hands back: a stage already normalized into
`ShipmentStage`, so provider-specific status codes never leak past this
point. `services.tracking.ingest_adapter_update` is what turns a
`NormalizedStatus` into a real update, by going through the same transition
service manual updates use.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from models.enums import ShipmentStage


@dataclass(frozen=True)
class NormalizedStatus:
    stage: ShipmentStage
    occurred_at: datetime
    note: str | None
    provider_reference: str


class TrackingAdapter(Protocol):
    def get_status(self, reference: str) -> "NormalizedStatus | None":
        """Return the latest known status for `reference`, or None if the
        provider has nothing to report."""
        ...
