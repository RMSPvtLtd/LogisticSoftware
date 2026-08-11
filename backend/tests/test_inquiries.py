from datetime import date

from app.models.enums import EventSource, ShipmentStage
from app.services.quotes import accept_quote, generate_quote
from app.services.transitions import advance_stage
from tests.factories import make_customer, make_inquiry, simple_rate_card

TODAY = date(2026, 6, 1)


def test_creating_an_inquiry_creates_a_shipment_at_inquiry_stage(db_session):
    customer = make_customer(db_session)
    inquiry = make_inquiry(db_session, customer)

    assert inquiry.shipment is not None
    assert inquiry.shipment.stage == ShipmentStage.INQUIRY
    assert inquiry.shipment.quote_id is None
    assert inquiry.shipment.job_number is None
    assert [e.stage for e in inquiry.shipment.status_events] == [ShipmentStage.INQUIRY]
    assert inquiry.shipment.status_events[0].source == EventSource.SYSTEM


def test_generating_a_quote_advances_shipment_to_quotation(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)

    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()

    assert inquiry.shipment.stage == ShipmentStage.QUOTATION
    assert inquiry.shipment.quote_id == quote.id


def test_regenerating_a_quote_does_not_re_transition_the_shipment(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)

    first_quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    assert inquiry.shipment.stage == ShipmentStage.QUOTATION
    n_events = len(inquiry.shipment.status_events)

    # Re-quoting (e.g. the first quote expired unaccepted) repoints
    # quote_id without adding a second QUOTATION event or changing stage.
    second_quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()

    assert inquiry.shipment.stage == ShipmentStage.QUOTATION
    assert inquiry.shipment.quote_id == second_quote.id
    assert inquiry.shipment.quote_id != first_quote.id
    assert len(inquiry.shipment.status_events) == n_events


def test_accepting_advances_shipment_to_job_opening_and_assigns_job_number(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()

    shipment = accept_quote(db_session, quote.id, "ops", today=TODAY)

    assert shipment.stage == ShipmentStage.JOB_OPENING
    assert shipment.job_number == "RAZ-2026-00001"
    assert inquiry.shipment.id == shipment.id


# --- ops invoice action ---


def _shipment_at_arrival(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    shipment = accept_quote(db_session, quote.id, "ops", today=TODAY)
    for stage in (
        ShipmentStage.AIRWAY_BILL, ShipmentStage.GD, ShipmentStage.PICKUP, ShipmentStage.GATE_IN,
        ShipmentStage.SHIPMENT_RECEIPT, ShipmentStage.WEIGHMENT, ShipmentStage.CUSTOMS_EXAMINATION,
        ShipmentStage.CUSTOMS_CLEARANCE, ShipmentStage.SCANNING, ShipmentStage.HANDOVER,
        ShipmentStage.DEPARTURE, ShipmentStage.TRANSHIPMENT, ShipmentStage.ARRIVAL,
    ):
        advance_stage(db_session, shipment, stage, actor="ops", note=None, source=EventSource.MANUAL)
    return shipment


def test_invoice_endpoint_succeeds_from_arrival(client, db_session):
    shipment = _shipment_at_arrival(db_session)
    db_session.commit()

    r = client.post(f"/shipments/{shipment.id}/invoice", json={"note": "Invoice sent"})
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == "invoice_to_customer"
    last_event = r.json()["status_events"][-1]
    assert last_event["source"] == "manual"
    assert last_event["note"] == "Invoice sent"


def test_invoice_endpoint_rejected_before_arrival(client, db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    shipment = accept_quote(db_session, quote.id, "ops", today=TODAY)
    db_session.commit()

    r = client.post(f"/shipments/{shipment.id}/invoice", json={})
    assert r.status_code == 409

    check = client.get(f"/shipments/{shipment.id}")
    assert check.json()["stage"] == "job_opening"
