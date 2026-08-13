from datetime import date

from models.enums import EventSource, Priority
from services.quotes import accept_quote, generate_quote
from services.transitions import set_priority
from factories import make_customer, make_inquiry, simple_rate_card

TODAY = date(2026, 6, 1)


def _accepted_shipment(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    return accept_quote(db_session, quote.id, "ops", today=TODAY)


def test_default_priority_is_medium(db_session):
    shipment = _accepted_shipment(db_session)
    assert shipment.priority == Priority.MEDIUM


def test_set_priority(db_session):
    shipment = _accepted_shipment(db_session)
    set_priority(db_session, shipment, priority=Priority.HIGH, actor="ops")

    assert shipment.priority == Priority.HIGH


def test_priority_change_creates_internal_history_event(db_session):
    shipment = _accepted_shipment(db_session)
    n_before = len(shipment.status_events)
    stage_before = shipment.stage

    set_priority(db_session, shipment, priority=Priority.LOW, actor="ops")

    assert len(shipment.status_events) == n_before + 1
    event = shipment.status_events[-1]
    assert event.source == EventSource.SYSTEM
    assert event.is_internal is True
    assert event.is_stage_change is False
    assert shipment.stage == stage_before  # priority change never touches stage


def test_priority_update_endpoint(client, db_session):
    shipment = _accepted_shipment(db_session)
    db_session.commit()

    r = client.post(f"/shipments/{shipment.id}/priority", json={"priority": "high"})
    assert r.status_code == 200, r.text
    assert r.json()["priority"] == "high"

    check = client.get(f"/shipments/{shipment.id}")
    assert check.json()["priority"] == "high"


def test_priority_filter_on_list_endpoint(client, db_session):
    low = _accepted_shipment(db_session)
    high = _accepted_shipment(db_session)
    db_session.commit()

    r = client.post(f"/shipments/{high.id}/priority", json={"priority": "high"})
    assert r.status_code == 200, r.text

    r = client.get("/shipments", params={"priority": "high"})
    assert r.status_code == 200, r.text
    ids = [s["id"] for s in r.json()]
    assert high.id in ids
    assert low.id not in ids
