"""Tracking domain logic: looking up a shipment by any of its reference
numbers, and turning a tracking adapter's normalized status into a real
shipment update. Kept separate from `integrations.tracking.protocol` so the adapter
layer stays free of any knowledge of Shipment/StatusEvent/the transition
rules — this module is what connects the two, and it does so through
`services.transitions.advance_stage`, never by writing to `Shipment.stage`
or `StatusEvent` directly.
"""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from integrations.tracking.protocol import TrackingAdapter
from utils.errors import AmbiguousTrackingReference, InvalidTransition, NotFound, TrackingIngestionFailed
from models.enums import EventSource
from models.shipment import Shipment, ShipmentReference, StatusEvent
from services.transitions import advance_stage

ADAPTER_ACTOR = "tracking-adapter"


def find_shipment_for_tracking(session: Session, reference: str) -> Shipment:
    """Exact-match lookup by job number or any shipment reference value.
    Never guesses: zero matches is a 404, more than one is a distinct
    ambiguity error rather than an arbitrary pick.
    """
    stmt = (
        select(Shipment)
        .outerjoin(ShipmentReference, ShipmentReference.shipment_id == Shipment.id)
        .where(or_(Shipment.job_number == reference, ShipmentReference.value == reference))
        .distinct()
    )
    matches = session.execute(stmt).scalars().all()
    if not matches:
        raise NotFound(f"No shipment found for reference {reference!r}")
    if len(matches) > 1:
        raise AmbiguousTrackingReference(
            f"Reference {reference!r} matches multiple shipments; a more specific reference is required"
        )
    return matches[0]


def ingest_adapter_update(
    session: Session, shipment: Shipment, adapter: TrackingAdapter, reference: str
) -> StatusEvent | None:
    """Fetch `reference` from `adapter` and, if it reports a stage, apply it
    through the same transition service manual updates use. Returns None if
    the adapter has nothing to report. Raises TrackingIngestionFailed
    — without mutating the shipment — if the provider's reported stage is
    not a valid next step (invalid, backwards, or skipped); the shipment
    transition rules cannot be bypassed by an automated source.
    """
    status = adapter.get_status(reference)
    if status is None:
        return None

    try:
        return advance_stage(
            session,
            shipment,
            status.stage,
            actor=ADAPTER_ACTOR,
            note=status.note,
            source=EventSource.AUTOMATED,
        )
    except InvalidTransition as exc:
        raise TrackingIngestionFailed(
            f"Adapter reported stage {status.stage.value} for reference {reference!r}, "
            f"which is not a valid next stage: {exc}"
        ) from exc
