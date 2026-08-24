"""The only writer of `Shipment.stage` after a shipment is created. Three
entry points touch `stage`, each producing exactly one new `StatusEvent`:

  advance_stage  -- normal progression, one step at a time, next-stage-only
  correct_stage  -- deliberate repair, may jump to any operational stage
  record_note    -- annotation only, never touches stage

set_risk, set_priority, set_hold, and cancel_shipment also live here since
they're the same kind of "independent of stage" shipment field, each
recording its change as a StatusEvent via record_note rather than a stage
change.

No function here updates or deletes an existing StatusEvent. Corrections and
notes are always new rows — this is what keeps shipment history append-only.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from utils.errors import InvalidCancellation, InvalidCorrection, InvalidTransition
from models.enums import CORRECTABLE_STAGES, EventSource, Priority, ShipmentStage, next_stage, previous_stage, stage_label
from models.shipment import Shipment, StatusEvent


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
    if shipment.is_cancelled:
        raise InvalidTransition(f"Shipment {shipment.id} is cancelled and cannot be advanced")
    if shipment.is_on_hold:
        raise InvalidTransition(f"Shipment {shipment.id} is on hold and cannot be advanced")

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
    CORRECTABLE_STAGES (job_opening onward) — correcting a shipment "back"
    to inquiry or quotation doesn't make operational sense once a job
    number has been issued. Not blocked by hold (this IS ops's explicit
    override), but a cancelled shipment is terminal even for corrections.
    """
    if shipment.is_cancelled:
        raise InvalidCorrection(f"Shipment {shipment.id} is cancelled and cannot be corrected")
    if not reason or not reason.strip():
        raise InvalidCorrection("A correction reason is required")
    if to_stage not in CORRECTABLE_STAGES:
        raise InvalidCorrection(f"{to_stage.value} is not a valid correction target")
    if to_stage == shipment.stage:
        raise InvalidCorrection(f"Shipment {shipment.id} is already at stage {to_stage.value}")

    previous = shipment.stage
    shipment.stage = to_stage
    event = StatusEvent(
        stage=to_stage,
        actor=actor,
        note=f"Corrected from {stage_label(previous)} to {stage_label(to_stage)}: {reason}",
        source=EventSource.CORRECTION,
        is_stage_change=True,
    )
    shipment.status_events.append(event)
    session.flush()
    return event


def cancel_shipment(
    session: Session,
    shipment: Shipment,
    *,
    reason: str,
    actor: str,
    customer_note: str | None = None,
) -> Shipment:
    """Terminal, independent of `stage` -- chosen over adding CANCELLED to
    ShipmentStage itself, which would break every place that does linear
    stage_index arithmetic (the tracking checklist, next_stage/previous_stage,
    worker-area lookup). `reason` is internal/audit-only and must never reach
    a customer surface; `customer_note` is the deliberately-written
    customer-safe text (defaults to a generic message if omitted -- see
    schemas.tracking). Two StatusEvent rows are recorded so the existing
    is_internal filtering in schemas.tracking.from_shipment does the right
    thing by construction, not because a filter remembered to exclude the
    internal one.
    """
    if shipment.is_cancelled:
        raise InvalidCancellation(f"Shipment {shipment.id} is already cancelled")
    if not reason or not reason.strip():
        raise InvalidCancellation("A cancellation reason is required")
    if shipment.stage == ShipmentStage.INVOICE_TO_CUSTOMER:
        raise InvalidCancellation(f"Shipment {shipment.id} has already been fully completed and cannot be cancelled")

    now = datetime.now(timezone.utc)
    shipment.is_cancelled = True
    shipment.cancelled_reason = reason
    shipment.customer_cancellation_note = customer_note
    shipment.cancelled_by = actor
    shipment.cancelled_at = now

    record_note(session, shipment, actor=actor, note=f"Cancelled: {reason}", source=EventSource.SYSTEM, is_internal=True)
    record_note(
        session, shipment, actor=actor,
        note=customer_note or "Shipment cancelled.", source=EventSource.SYSTEM, is_internal=False,
    )
    return shipment


def set_hold(
    session: Session, shipment: Shipment, *, on_hold: bool, reason: str | None, actor: str
) -> Shipment:
    """Set or clear the operational hold flag, independent of stage --
    mirrors `set_risk`'s exact shape. A held shipment can't be advanced by a
    worker (see advance_stage); ops's correct_stage remains unaffected, since
    hold is meant to pause normal progression, not block a deliberate fix.
    """
    now = datetime.now(timezone.utc)
    shipment.is_on_hold = on_hold
    if on_hold:
        shipment.hold_reason = reason
        shipment.hold_created_by = actor
        shipment.hold_created_at = now
        shipment.hold_removed_by = None
        shipment.hold_removed_at = None
        note = f"Placed on hold: {reason}" if reason else "Placed on hold"
    else:
        shipment.hold_removed_by = actor
        shipment.hold_removed_at = now
        note = "Hold removed"

    record_note(session, shipment, actor=actor, note=note, source=EventSource.SYSTEM, is_internal=True)
    return shipment


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


def set_priority(session: Session, shipment: Shipment, *, priority: Priority, actor: str) -> Shipment:
    """Set the shipment's priority, independent of stage. Unlike risk, there
    is no "cleared" state — a shipment always holds exactly one of the
    three levels, defaulting to MEDIUM at creation.
    """
    shipment.priority = priority
    record_note(
        session, shipment, actor=actor,
        note=f"Priority set to {priority.value}", source=EventSource.SYSTEM, is_internal=True,
    )
    return shipment
