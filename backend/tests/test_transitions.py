from datetime import date

import pytest

from app.errors import InvalidCorrection, InvalidTransition
from app.models.enums import EventSource, OPERATIONAL_STAGE_ORDER, ShipmentStage, TransportMode
from app.services.quotes import accept_quote, generate_quote
from app.services.transitions import advance_stage, correct_stage
from tests.factories import make_area, make_customer, make_inquiry, make_worker, simple_rate_card

TODAY = date(2026, 6, 1)

# Every stage a shipment moves through after job_opening, in order.
VALID_STEPS = list(OPERATIONAL_STAGE_ORDER[OPERATIONAL_STAGE_ORDER.index(ShipmentStage.JOB_OPENING) + 1 :])


def _accepted_shipment(db_session, **inquiry_overrides):
    customer = make_customer(db_session)
    simple_rate_card(db_session, mode=inquiry_overrides.get("mode", TransportMode.AIR))
    inquiry = make_inquiry(db_session, customer, **inquiry_overrides)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    return accept_quote(db_session, quote.id, "ops", today=TODAY)


def test_all_valid_steps_progress_in_order(db_session):
    shipment = _accepted_shipment(db_session)
    for stage in VALID_STEPS:
        advance_stage(db_session, shipment, stage, actor="ops", note=None, source=EventSource.MANUAL)
        assert shipment.stage == stage
    # inquiry, quotation, job_opening events already exist before this walk starts
    assert len(shipment.status_events) == 3 + len(VALID_STEPS)


def test_sea_shipment_walks_the_identical_stage_order(db_session):
    # Sea reuses OPERATIONAL_STAGE_ORDER as-is -- transitions don't care
    # about mode at all, only display labels differ (see test_tracking.py).
    shipment = _accepted_shipment(db_session, mode=TransportMode.SEA)
    assert shipment.mode == TransportMode.SEA
    for stage in VALID_STEPS:
        advance_stage(db_session, shipment, stage, actor="ops", note=None, source=EventSource.MANUAL)
        assert shipment.stage == stage
    assert shipment.stage == ShipmentStage.INVOICE_TO_CUSTOMER


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
    advance_stage(db_session, shipment, ShipmentStage.GD, actor="ops", note="declared", source=EventSource.MANUAL)

    events = shipment.status_events
    assert [e.stage for e in events] == [
        ShipmentStage.INQUIRY, ShipmentStage.QUOTATION, ShipmentStage.JOB_OPENING,
        ShipmentStage.AIRWAY_BILL, ShipmentStage.GD,
    ]
    assert events[0].id == initial_event_id
    assert events == sorted(events, key=lambda e: e.timestamp)


# --- corrections ---


def test_correction_moves_to_arbitrary_valid_stage(db_session):
    shipment = _accepted_shipment(db_session)
    advance_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", note=None, source=EventSource.MANUAL)
    advance_stage(db_session, shipment, ShipmentStage.GD, actor="ops", note=None, source=EventSource.MANUAL)
    ids_before = [e.id for e in shipment.status_events]

    event = correct_stage(
        db_session, shipment, ShipmentStage.PICKUP, actor="ops", reason="cargo already picked up, status was stale"
    )

    assert shipment.stage == ShipmentStage.PICKUP
    assert event.source == EventSource.CORRECTION
    assert event.is_stage_change is True
    assert "cargo already picked up" in event.note
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


# --- server-controlled event source (API layer) ---
#
# Normal advancement is worker-only now (no ops "advance to next stage"
# endpoint exists — see app.api.shipments) so this is exercised against the
# worker portal's complete endpoint, the only remaining path a caller could
# try to spoof `source` through.


def test_caller_cannot_spoof_event_source_via_worker_complete(client, db_session):
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
    )
    assert r.status_code == 201, r.text
    inquiry_id = r.json()["id"]

    r = client.post("/quotes/generate", json={"inquiry_id": inquiry_id})
    assert r.status_code == 201, r.text
    quote_id = r.json()["id"]

    r = client.post(f"/quotes/{quote_id}/accept")
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

    check = client.get(f"/shipments/{shipment_id}")
    event = next(e for e in check.json()["status_events"] if e["stage"] == "airway_bill")
    assert event["source"] == "manual", "a client-supplied 'source' field must never override the server's choice"
    assert event["actor"] != "correction"
