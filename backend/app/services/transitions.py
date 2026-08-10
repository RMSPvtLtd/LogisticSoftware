"""The only writer of `Shipment.stage` after a shipment is created. Three
entry points, each producing exactly one new `StatusEvent`:

  advance_stage  -- normal progression, one step at a time, next-stage-only
  correct_stage  -- deliberate repair, may jump to any operational stage
  record_note    -- annotation only, never touches stage

No function here updates or deletes an existing StatusEvent. Corrections and
notes are always new rows — this is what keeps shipment history append-only.
"""

from sqlalchemy.orm import Session

from app.errors import InvalidCorrection, InvalidTransition
from app.models.enums import EventSource, OPERATIONAL_STAGE_ORDER, ShipmentStage, next_stage
from app.models.shipment import Shipment, StatusEvent


def advance_stage(
    session: Session,
    shipment: Shipment,
    to_stage: ShipmentStage,
    *,
    actor: str,
    note: str | None,
    source: EventSource,
) -> StatusEvent:
    """Move `shipment` to its immediate next operational stage. `source` is
    supplied by the calling operation (the manual-update route passes
    MANUAL, adapter ingestion passes AUTOMATED) — it is never taken from a
    request body, since it is part of the audit trail.
    """
    expected = next_stage(shipment.stage)
    if expected is None or to_stage != expected:
        current = shipment.stage.value
        raise InvalidTransition(
            f"Shipment {shipment.id} cannot move from {current} to {to_stage.value}; "
            f"the only valid next stage is {expected.value if expected else 'none (already delivered)'}"
        )

    shipment.stage = to_stage
    event = StatusEvent(stage=to_stage, actor=actor, note=note, source=source, is_stage_change=True)
    # Appended through the relationship (not a raw shipment_id=... FK) so
    # shipment.status_events reflects the new row immediately within this
    # session, even if the collection was already loaded earlier.
    shipment.status_events.append(event)
    session.flush()
    return event


def correct_stage(
    session: Session,
    shipment: Shipment,
    to_stage: ShipmentStage,
    *,
    actor: str,
    reason: str,
) -> StatusEvent:
    """Repair path: bypasses the next-stage-only rule to fix an operational
    mistake, while still producing a full audit trail entry. Restricted to
    the operational stage range (job_opened..delivered) — a Shipment only
    ever exists once a quote is accepted, so `inquiry`/`quoted` are not
    valid targets for a shipment correction.
    """
    if not reason or not reason.strip():
        raise InvalidCorrection("A correction reason is required")
    if to_stage not in OPERATIONAL_STAGE_ORDER:
        raise InvalidCorrection(f"{to_stage.value} is not a valid shipment stage")
    if to_stage == shipment.stage:
        raise InvalidCorrection(f"Shipment {shipment.id} is already at stage {to_stage.value}")

    shipment.stage = to_stage
    event = StatusEvent(
        stage=to_stage, actor=actor, note=reason, source=EventSource.CORRECTION, is_stage_change=True
    )
    shipment.status_events.append(event)
    session.flush()
    return event


def record_note(
    session: Session,
    shipment: Shipment,
    *,
    actor: str,
    note: str,
    source: EventSource,
    is_internal: bool = False,
) -> StatusEvent:
    """Add an annotation at the shipment's current stage. Never mutates
    `Shipment.stage` and never touches an existing row.
    """
    event = StatusEvent(
        stage=shipment.stage,
        actor=actor,
        note=note,
        source=source,
        is_stage_change=False,
        is_internal=is_internal,
    )
    shipment.status_events.append(event)
    session.flush()
    return event


def set_risk(
    session: Session,
    shipment: Shipment,
    *,
    is_at_risk: bool,
    risk_reason: str | None,
    actor: str,
) -> Shipment:
    """Set or clear the at-risk flag, independent of stage. `risk_reason` is
    internal-only and the note recording this change is marked internal so
    it never reaches the customer-safe tracking history. Per the event
    source rules, this is recorded as a system note even though an ops user
    triggered it — the risk flag itself, not the note, is what the API
    treats as the manually-controlled fact.
    """
    shipment.is_at_risk = is_at_risk
    shipment.risk_reason = risk_reason if is_at_risk else None

    note = f"Marked at risk: {risk_reason}" if is_at_risk else "Risk cleared"
    record_note(session, shipment, actor=actor, note=note, source=EventSource.SYSTEM, is_internal=True)
    return shipment
