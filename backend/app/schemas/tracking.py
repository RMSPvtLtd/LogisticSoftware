"""The customer-safe view of a shipment. Deliberately independent of every
internal schema (`schemas/shipments.py`, `schemas/quotes.py`) — nothing here
is inherited or reused from them, so an internal field can never leak into
this response just because a shared base class happened to include it.

Excluded by construction: quote, pricing, subtotal, markup, totals,
line-item prices, internal notes, risk_reason, customer account data, and
any other staff-only information. Only `at_risk` (the boolean) crosses the
boundary; `risk_reason` does not.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.enums import OPERATIONAL_STAGE_ORDER, ReferenceType, ShipmentStage, TransportMode, stage_index
from app.models.shipment import Shipment

ChecklistStatus = Literal["completed", "current", "upcoming"]


class TrackingChecklistItem(BaseModel):
    stage: ShipmentStage
    status: ChecklistStatus


class TrackingReference(BaseModel):
    type: ReferenceType
    value: str


class TrackingEvent(BaseModel):
    stage: ShipmentStage
    timestamp: datetime
    note: str | None


class TrackingResult(BaseModel):
    job_number: str
    origin: str
    destination: str
    mode: TransportMode
    stage: ShipmentStage
    checklist: list[TrackingChecklistItem]
    status_history: list[TrackingEvent]
    references: list[TrackingReference]
    at_risk: bool


def _build_checklist(current_stage: ShipmentStage) -> list[TrackingChecklistItem]:
    current_position = stage_index(current_stage)
    items = []
    for stage in OPERATIONAL_STAGE_ORDER:
        position = stage_index(stage)
        if position < current_position:
            status: ChecklistStatus = "completed"
        elif position == current_position:
            status = "current"
        else:
            status = "upcoming"
        items.append(TrackingChecklistItem(stage=stage, status=status))
    return items


def from_shipment(shipment: Shipment) -> TrackingResult:
    """Build a customer-safe result field by field from a Shipment. Internal
    notes (StatusEvent.is_internal) are dropped here, not filtered by the
    caller — this is the one place that decision is made.
    """
    history = [
        TrackingEvent(stage=event.stage, timestamp=event.timestamp, note=event.note)
        for event in shipment.status_events
        if not event.is_internal
    ]
    references = [
        TrackingReference(type=ref.type, value=ref.value)
        for ref in shipment.references
        if ref.type != ReferenceType.JOB_NUMBER  # job_number is already the top-level field
    ]

    return TrackingResult(
        job_number=shipment.job_number,
        origin=shipment.inquiry.origin,
        destination=shipment.inquiry.destination,
        mode=shipment.inquiry.mode,
        stage=shipment.stage,
        checklist=_build_checklist(shipment.stage),
        status_history=history,
        references=references,
        at_risk=shipment.is_at_risk,
    )
