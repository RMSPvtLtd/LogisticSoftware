from datetime import date

import pytest

from utils.errors import InvalidCancellation, InvalidCorrection, InvalidTransition
from models.enums import EventSource, OPERATIONAL_STAGE_ORDER, ShipmentStage
from services.quotes import accept_quote, generate_quote
from services.transitions import advance_stage, cancel_shipment, correct_stage, set_hold
from factories import make_area, make_customer, make_inquiry, make_worker, simple_rate_card

TODAY = date(2026, 6, 1)

# Every stage a shipment moves through after job_opening, in order.
VALID_STEPS = list(OPERATIONAL_STAGE_ORDER[OPERATIONAL_STAGE_ORDER.index(ShipmentStage.JOB_OPENING) + 1 :])


def _accepted_shipment(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    return accept_quote(db_session, quote.id, "ops", today=TODAY)


def test_all_valid_steps_progress_in_order(db_session):
    shipment = _accepted_shipment(db_session)
    for stage in VALID_STEPS:
        advance_stage(db_session, shipment, stage, actor="ops", note=None, source=EventSource.MANUAL)
        assert shipment.stage == stage
    # inquiry, quotation, job_opening, accepted events already exist before this walk starts
    assert len(shipment.status_events) == 4 + len(VALID_STEPS)


@pytest.mark.parametrize(
    "from_stage,attempted",
    [
        (ShipmentStage.JOB_OPENING, ShipmentStage.INVOICE_TO_CUSTOMER),
        (ShipmentStage.CUSTOMS_EXAMINATION, ShipmentStage.SCANNING),
    ],
)
def test_skip_ahead_and_backwards_rejected(db_session, from_stage, attempted):
    shipment = _accepted_shipment(db_session)
    # Walk to from_stage first.
    idx = VALID_STEPS.index(from_stage) if from_stage in VALID_STEPS else -1
    for stage in VALID_STEPS[: idx + 1]:
        advance_stage(db_session, shipment, stage, actor="ops", note=None, source=EventSource.MANUAL)
    assert shipment.stage == from_stage

    with pytest.raises(InvalidTransition):
        advance_stage(db_session, shipment, attempted, actor="ops", note=None, source=EventSource.MANUAL)
    assert shipment.stage == from_stage


def test_repeated_stage_rejected(db_session):
    shipment = _accepted_shipment(db_session)
    advance_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", note=None, source=EventSource.MANUAL)

    with pytest.raises(InvalidTransition):
        advance_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", note=None, source=EventSource.MANUAL)


def test_transition_out_of_terminal_stage_rejected(db_session):
    shipment = _accepted_shipment(db_session)
    for stage in VALID_STEPS:
        advance_stage(db_session, shipment, stage, actor="ops", note=None, source=EventSource.MANUAL)
    assert shipment.stage == ShipmentStage.INVOICE_TO_CUSTOMER

    with pytest.raises(InvalidTransition):
        advance_stage(db_session, shipment, ShipmentStage.INVOICE_TO_CUSTOMER, actor="ops", note=None, source=EventSource.MANUAL)


def test_advance_stage_creates_event_and_preserves_prior_events(db_session):
    shipment = _accepted_shipment(db_session)
    initial_event_id = shipment.status_events[0].id

    advance_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", note="filed", source=EventSource.MANUAL)
    advance_stage(db_session, shipment, ShipmentStage.PICKUP, actor="ops", note="picked up", source=EventSource.MANUAL)

    events = shipment.status_events
    assert [e.stage for e in events] == [
        # The second JOB_OPENING is the non-stage-change "quote accepted"
        # audit note (services.quotes.accept_quote), not a repeated transition.
        ShipmentStage.INQUIRY, ShipmentStage.QUOTATION, ShipmentStage.JOB_OPENING, ShipmentStage.JOB_OPENING,
        ShipmentStage.AIRWAY_BILL, ShipmentStage.PICKUP,
    ]
    assert events[0].id == initial_event_id
    assert events == sorted(events, key=lambda e: e.timestamp)


# --- corrections ---


def test_correction_moves_to_arbitrary_valid_stage(db_session):
    shipment = _accepted_shipment(db_session)
    advance_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", note=None, source=EventSource.MANUAL)
    advance_stage(db_session, shipment, ShipmentStage.PICKUP, actor="ops", note=None, source=EventSource.MANUAL)
    ids_before = [e.id for e in shipment.status_events]

    event = correct_stage(
        db_session, shipment, ShipmentStage.GATE_IN, actor="ops", reason="cargo already gated in, status was stale"
    )

    assert shipment.stage == ShipmentStage.GATE_IN
    assert event.source == EventSource.CORRECTION
    assert event.is_stage_change is True
    assert "cargo already gated in" in event.note
    assert [e.id for e in shipment.status_events[: len(ids_before)]] == ids_before


def test_correction_cannot_target_inquiry_or_quotation(db_session):
    shipment = _accepted_shipment(db_session)
    with pytest.raises(InvalidCorrection):
        correct_stage(db_session, shipment, ShipmentStage.INQUIRY, actor="ops", reason="test")
    with pytest.raises(InvalidCorrection):
        correct_stage(db_session, shipment, ShipmentStage.QUOTATION, actor="ops", reason="test")


def test_correction_same_stage_rejected(db_session):
    shipment = _accepted_shipment(db_session)
    with pytest.raises(InvalidCorrection):
        correct_stage(db_session, shipment, ShipmentStage.JOB_OPENING, actor="ops", reason="no-op")


def test_correction_blank_reason_rejected(db_session):
    shipment = _accepted_shipment(db_session)
    with pytest.raises(InvalidCorrection):
        correct_stage(db_session, shipment, ShipmentStage.PICKUP, actor="ops", reason="   ")


# --- cancellation ---


def test_cancel_sets_fields_and_keeps_stage(db_session):
    shipment = _accepted_shipment(db_session)
    advance_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", note=None, source=EventSource.MANUAL)

    cancel_shipment(db_session, shipment, reason="Customer cancelled order", actor="ops")

    assert shipment.is_cancelled is True
    assert shipment.stage == ShipmentStage.AIRWAY_BILL, "cancellation must not overwrite the current stage"
    assert shipment.cancelled_reason == "Customer cancelled order"
    assert shipment.cancelled_by == "ops"
    assert shipment.cancelled_at is not None


def test_cancel_keeps_internal_reason_separate_from_customer_note(db_session):
    shipment = _accepted_shipment(db_session)
    cancel_shipment(
        db_session, shipment, reason="Customer failed to pay after repeated reminders",
        actor="ops", customer_note="Shipment cancelled at customer's request.",
    )

    internal_events = [e for e in shipment.status_events if e.is_internal]
    public_events = [e for e in shipment.status_events if not e.is_internal]

    assert any("repeated reminders" in e.note for e in internal_events)
    assert not any("repeated reminders" in e.note for e in public_events)
    assert any(e.note == "Shipment cancelled at customer's request." for e in public_events)


def test_cancel_falls_back_to_generic_customer_note(db_session):
    shipment = _accepted_shipment(db_session)
    cancel_shipment(db_session, shipment, reason="Internal reason only", actor="ops")

    public_events = [e for e in shipment.status_events if not e.is_internal]
    assert any(e.note == "Shipment cancelled." for e in public_events)
    assert not any("Internal reason only" in e.note for e in public_events)


def test_cancel_requires_a_reason(db_session):
    shipment = _accepted_shipment(db_session)
    with pytest.raises(InvalidCancellation):
        cancel_shipment(db_session, shipment, reason="  ", actor="ops")


def test_cannot_cancel_an_already_cancelled_shipment(db_session):
    shipment = _accepted_shipment(db_session)
    cancel_shipment(db_session, shipment, reason="First", actor="ops")
    with pytest.raises(InvalidCancellation):
        cancel_shipment(db_session, shipment, reason="Second", actor="ops")


def test_cannot_cancel_a_fully_completed_shipment(db_session):
    shipment = _accepted_shipment(db_session)
    for stage in VALID_STEPS:
        advance_stage(db_session, shipment, stage, actor="ops", note=None, source=EventSource.MANUAL)
    assert shipment.stage == ShipmentStage.INVOICE_TO_CUSTOMER

    with pytest.raises(InvalidCancellation):
        cancel_shipment(db_session, shipment, reason="too late", actor="ops")


def test_cancelled_shipment_cannot_be_advanced(db_session):
    shipment = _accepted_shipment(db_session)
    cancel_shipment(db_session, shipment, reason="Order cancelled", actor="ops")

    with pytest.raises(InvalidTransition):
        advance_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", note=None, source=EventSource.MANUAL)


def test_cancelled_shipment_cannot_be_corrected(db_session):
    shipment = _accepted_shipment(db_session)
    cancel_shipment(db_session, shipment, reason="Order cancelled", actor="ops")

    with pytest.raises(InvalidCorrection):
        correct_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", reason="test")


def test_cancel_endpoint(client, db_session, ops_headers):
    shipment = _accepted_shipment(db_session)
    db_session.commit()

    r = client.post(
        f"/shipments/{shipment.id}/cancel",
        json={"reason": "Customer cancelled the order", "customer_note": "Shipment cancelled."},
        headers=ops_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_cancelled"] is True
    assert r.json()["cancelled_reason"] == "Customer cancelled the order"


# --- hold ---


def test_hold_blocks_advancement_but_not_correction(db_session):
    shipment = _accepted_shipment(db_session)
    set_hold(db_session, shipment, on_hold=True, reason="Missing customs document", actor="ops")

    assert shipment.is_on_hold is True
    with pytest.raises(InvalidTransition):
        advance_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", note=None, source=EventSource.MANUAL)

    # Ops corrections are an explicit override and remain unaffected by hold.
    correct_stage(db_session, shipment, ShipmentStage.PICKUP, actor="ops", reason="documented exception")
    assert shipment.stage == ShipmentStage.PICKUP


def test_removing_hold_allows_advancement_again(db_session):
    shipment = _accepted_shipment(db_session)
    set_hold(db_session, shipment, on_hold=True, reason="Missing customs document", actor="ops")
    set_hold(db_session, shipment, on_hold=False, reason=None, actor="ops")

    assert shipment.is_on_hold is False
    advance_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", note=None, source=EventSource.MANUAL)
    assert shipment.stage == ShipmentStage.AIRWAY_BILL


def test_hold_records_creator_and_timestamps(db_session):
    shipment = _accepted_shipment(db_session)
    set_hold(db_session, shipment, on_hold=True, reason="Waiting on broker signature", actor="ops-a")
    assert shipment.hold_created_by == "ops-a"
    assert shipment.hold_created_at is not None
    assert shipment.hold_removed_by is None

    set_hold(db_session, shipment, on_hold=False, reason=None, actor="ops-b")
    assert shipment.hold_removed_by == "ops-b"
    assert shipment.hold_removed_at is not None


def test_hold_reason_is_internal_only(db_session):
    shipment = _accepted_shipment(db_session)
    set_hold(db_session, shipment, on_hold=True, reason="Waiting on broker signature", actor="ops")

    hold_events = [e for e in shipment.status_events if "Waiting on broker signature" in (e.note or "")]
    assert len(hold_events) == 1
    assert hold_events[0].is_internal is True


def test_hold_endpoint(client, db_session, ops_headers):
    shipment = _accepted_shipment(db_session)
    db_session.commit()

    r = client.post(
        f"/shipments/{shipment.id}/hold", json={"on_hold": True, "reason": "Missing document"}, headers=ops_headers
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_on_hold"] is True

    r = client.post(f"/shipments/{shipment.id}/hold", json={"on_hold": False}, headers=ops_headers)
    assert r.status_code == 200, r.text
    assert r.json()["is_on_hold"] is False


# --- server-controlled event source (API layer) ---
#
# Normal advancement is worker-only now (no ops "advance to next stage"
# endpoint exists — see api.shipments) so this is exercised against the
# worker portal's complete endpoint, the only remaining path a caller could
# try to spoof `source` through.


def test_caller_cannot_spoof_event_source_via_worker_complete(client, db_session, ops_headers):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    airway_bill_area = make_area(db_session, ShipmentStage.AIRWAY_BILL)
    make_worker(db_session, airway_bill_area, username="ali.airwaybill", password="Correct123!")
    db_session.commit()  # visible to the client's own session (shared in-memory engine)

    r = client.post(
        "/inquiries",
        json={
            "customer_id": customer.id, "origin": "Lahore", "destination": "Dubai", "mode": "air",
            "cargo_type": "general", "weight_kg": "100", "volume_cbm": "0.2", "incoterm": "DAP",
        },
        headers=ops_headers,
    )
    assert r.status_code == 201, r.text
    inquiry_id = r.json()["id"]

    r = client.post("/quotes/generate", json={"inquiry_id": inquiry_id}, headers=ops_headers)
    assert r.status_code == 201, r.text
    quote_id = r.json()[0]["id"]

    r = client.post(f"/quotes/{quote_id}/accept", headers=ops_headers)
    assert r.status_code == 200, r.text
    shipment_id = r.json()["id"]

    login = client.post("/auth/login", json={"username": "ali.airwaybill", "password": "Correct123!"})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    r = client.post(
        f"/worker/shipments/{shipment_id}/complete",
        json={"note": "filed", "source": "correction"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

    check = client.get(f"/shipments/{shipment_id}", headers=ops_headers)
    event = next(e for e in check.json()["status_events"] if e["stage"] == "airway_bill")
    assert event["source"] == "manual", "a client-supplied 'source' field must never override the server's choice"
    assert event["actor"] != "correction"
