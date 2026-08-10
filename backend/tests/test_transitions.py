from datetime import date

import pytest

from app.errors import InvalidCorrection, InvalidTransition
from app.models.enums import EventSource, ShipmentStage
from app.services.quotes import accept_quote, generate_quote
from app.services.transitions import advance_stage, correct_stage
from tests.factories import make_area, make_customer, make_inquiry, make_worker, simple_rate_card

TODAY = date(2026, 6, 1)

VALID_STEPS = [
    ShipmentStage.DOCS_FILED,
    ShipmentStage.PICKED_UP,
    ShipmentStage.IN_TRANSIT,
    ShipmentStage.CUSTOMS_CLEARANCE,
    ShipmentStage.ARRIVED,
    ShipmentStage.DELIVERED,
]


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
    assert len(shipment.status_events) == 1 + len(VALID_STEPS)  # + initial job_opened event


@pytest.mark.parametrize(
    "from_stage,attempted",
    [
        (ShipmentStage.JOB_OPENED, ShipmentStage.DELIVERED),
        (ShipmentStage.IN_TRANSIT, ShipmentStage.PICKED_UP),
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
    advance_stage(db_session, shipment, ShipmentStage.DOCS_FILED, actor="ops", note=None, source=EventSource.MANUAL)

    with pytest.raises(InvalidTransition):
        advance_stage(db_session, shipment, ShipmentStage.DOCS_FILED, actor="ops", note=None, source=EventSource.MANUAL)


def test_transition_out_of_delivered_rejected(db_session):
    shipment = _accepted_shipment(db_session)
    for stage in VALID_STEPS:
        advance_stage(db_session, shipment, stage, actor="ops", note=None, source=EventSource.MANUAL)
    assert shipment.stage == ShipmentStage.DELIVERED

    with pytest.raises(InvalidTransition):
        advance_stage(db_session, shipment, ShipmentStage.DELIVERED, actor="ops", note=None, source=EventSource.MANUAL)


def test_advance_stage_creates_event_and_preserves_prior_events(db_session):
    shipment = _accepted_shipment(db_session)
    initial_event_id = shipment.status_events[0].id

    advance_stage(db_session, shipment, ShipmentStage.DOCS_FILED, actor="ops", note="filed", source=EventSource.MANUAL)
    advance_stage(db_session, shipment, ShipmentStage.PICKED_UP, actor="ops", note="picked", source=EventSource.MANUAL)

    events = shipment.status_events
    assert [e.stage for e in events] == [ShipmentStage.JOB_OPENED, ShipmentStage.DOCS_FILED, ShipmentStage.PICKED_UP]
    assert events[0].id == initial_event_id
    assert events == sorted(events, key=lambda e: e.timestamp)


# --- corrections ---


def test_correction_moves_to_arbitrary_valid_stage(db_session):
    shipment = _accepted_shipment(db_session)
    advance_stage(db_session, shipment, ShipmentStage.DOCS_FILED, actor="ops", note=None, source=EventSource.MANUAL)
    advance_stage(db_session, shipment, ShipmentStage.PICKED_UP, actor="ops", note=None, source=EventSource.MANUAL)
    ids_before = [e.id for e in shipment.status_events]

    event = correct_stage(
        db_session, shipment, ShipmentStage.IN_TRANSIT, actor="ops", reason="cargo already departed, status was stale"
    )

    assert shipment.stage == ShipmentStage.IN_TRANSIT
    assert event.source == EventSource.CORRECTION
    assert event.is_stage_change is True
    assert "cargo already departed" in event.note
    assert [e.id for e in shipment.status_events[: len(ids_before)]] == ids_before


def test_correction_same_stage_rejected(db_session):
    shipment = _accepted_shipment(db_session)
    with pytest.raises(InvalidCorrection):
        correct_stage(db_session, shipment, ShipmentStage.JOB_OPENED, actor="ops", reason="no-op")


def test_correction_blank_reason_rejected(db_session):
    shipment = _accepted_shipment(db_session)
    with pytest.raises(InvalidCorrection):
        correct_stage(db_session, shipment, ShipmentStage.IN_TRANSIT, actor="ops", reason="   ")


# --- server-controlled event source (API layer) ---
#
# Normal advancement is worker-only now (no ops "advance to next stage"
# endpoint exists — see app.api.shipments) so this is exercised against the
# worker portal's complete endpoint, the only remaining path a caller could
# try to spoof `source` through.


def test_caller_cannot_spoof_event_source_via_worker_complete(client, db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    docs_area = make_area(db_session, ShipmentStage.DOCS_FILED)
    make_worker(db_session, docs_area, username="ali.docs", password="Correct123!")
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

    login = client.post("/auth/login", json={"username": "ali.docs", "password": "Correct123!"})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    r = client.post(
        f"/worker/shipments/{shipment_id}/complete",
        json={"note": "filed", "source": "correction"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

    check = client.get(f"/shipments/{shipment_id}")
    docs_event = next(e for e in check.json()["status_events"] if e["stage"] == "docs_filed")
    assert docs_event["source"] == "manual", "a client-supplied 'source' field must never override the server's choice"
    assert docs_event["actor"] != "correction"
