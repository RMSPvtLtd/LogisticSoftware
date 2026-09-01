from datetime import date

from models.enums import EventSource, OPERATIONAL_STAGE_ORDER, ShipmentStage
from services.quotes import accept_quote, generate_quote
from services.transitions import advance_stage
from factories import make_customer, make_inquiry, simple_rate_card

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
    # shipment.quote_id is set only on acceptance (services.quotes.accept_quote)
    # -- not at generation time, so several sibling carrier quotes can exist
    # with none of them yet "the" quote. shipment_stage reads through the
    # inquiry instead (see Quote.shipment_stage's docstring).
    assert inquiry.shipment.quote_id is None
    assert quote.shipment_stage == ShipmentStage.QUOTATION


def test_regenerating_a_quote_does_not_re_transition_the_shipment(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)

    first_quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    assert inquiry.shipment.stage == ShipmentStage.QUOTATION
    n_events = len(inquiry.shipment.status_events)

    # Re-quoting (e.g. the first quote expired unaccepted) repoints
    # quote_id without changing stage -- it's a revision, which does add one
    # internal audit note (see services.quotes.generate_quote) but not a
    # second QUOTATION stage-change event.
    second_quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()

    assert inquiry.shipment.stage == ShipmentStage.QUOTATION
    # Neither quote has been accepted -- shipment.quote_id stays unset for both.
    assert inquiry.shipment.quote_id is None
    assert second_quote.revision_number == first_quote.revision_number + 1
    assert second_quote.root_quote_id == first_quote.id
    assert first_quote.superseded_at is not None
    assert len(inquiry.shipment.status_events) == n_events + 1


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
    # Every stage between job_opening (exclusive) and arrival (inclusive), in
    # pipeline order -- a slice of the single source of truth rather than a
    # literal list, so this can never drift from OPERATIONAL_STAGE_ORDER.
    start = OPERATIONAL_STAGE_ORDER.index(ShipmentStage.JOB_OPENING) + 1
    end = OPERATIONAL_STAGE_ORDER.index(ShipmentStage.ARRIVAL) + 1
    for stage in OPERATIONAL_STAGE_ORDER[start:end]:
        advance_stage(db_session, shipment, stage, actor="ops", note=None, source=EventSource.MANUAL)
    return shipment


def test_invoice_endpoint_succeeds_from_arrival(client, db_session, ops_headers):
    shipment = _shipment_at_arrival(db_session)
    db_session.commit()

    r = client.post(f"/shipments/{shipment.id}/invoice", json={"note": "Invoice sent"}, headers=ops_headers)
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == "invoice_to_customer"
    last_event = r.json()["status_events"][-1]
    assert last_event["source"] == "manual"
    assert last_event["note"] == "Invoice sent"


def test_invoice_endpoint_rejected_before_arrival(client, db_session, ops_headers):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    shipment = accept_quote(db_session, quote.id, "ops", today=TODAY)
    db_session.commit()

    r = client.post(f"/shipments/{shipment.id}/invoice", json={}, headers=ops_headers)
    assert r.status_code == 409

    check = client.get(f"/shipments/{shipment.id}", headers=ops_headers)
    assert check.json()["stage"] == "job_opening"
