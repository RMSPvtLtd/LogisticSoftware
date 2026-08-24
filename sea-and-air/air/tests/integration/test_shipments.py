from datetime import date

import pytest
from sqlalchemy import select

import models as m
from utils.errors import NotFound, ShipmentHasInvoice
from services.invoices import create_invoice_from_quote
from services.quotes import accept_quote, generate_quote
from services.shipments import delete_shipment
from factories import make_company, make_customer, make_inquiry, simple_rate_card

TODAY = date(2026, 6, 1)


def test_delete_shipment_removes_it_with_its_inquiry_and_quotes(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    shipment_id = inquiry.shipment.id
    quote_id = quote.id
    inquiry_id = inquiry.id
    db_session.flush()

    delete_shipment(db_session, shipment_id)
    db_session.flush()

    assert db_session.get(m.Shipment, shipment_id) is None
    assert db_session.get(m.Inquiry, inquiry_id) is None
    assert db_session.get(m.Quote, quote_id) is None


def test_delete_shipment_removes_every_revision(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    rev1 = generate_quote(db_session, inquiry.id, today=TODAY)
    rev2 = generate_quote(db_session, inquiry.id, today=TODAY)  # supersedes rev1
    shipment_id = inquiry.shipment.id
    db_session.flush()

    delete_shipment(db_session, shipment_id)
    db_session.flush()

    assert db_session.get(m.Quote, rev1.id) is None
    assert db_session.get(m.Quote, rev2.id) is None


def test_delete_shipment_not_found(db_session):
    with pytest.raises(NotFound):
        delete_shipment(db_session, 999999)


def test_delete_shipment_refuses_when_a_quote_has_an_invoice(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    company = make_company(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    accept_quote(db_session, quote.id, actor="ops", today=TODAY)
    create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)
    shipment_id = inquiry.shipment.id
    db_session.flush()

    with pytest.raises(ShipmentHasInvoice):
        delete_shipment(db_session, shipment_id)

    # Nothing was touched.
    assert db_session.get(m.Shipment, shipment_id) is not None


def test_delete_shipment_endpoint(client, db_session, ops_headers):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    db_session.commit()

    shipment_id = db_session.execute(
        select(m.Shipment).where(m.Shipment.inquiry_id == inquiry.id)
    ).scalar_one().id

    r = client.delete(f"/shipments/{shipment_id}", headers=ops_headers)
    assert r.status_code == 204, r.text

    r = client.get(f"/shipments/{shipment_id}", headers=ops_headers)
    assert r.status_code == 404


def test_delete_shipment_endpoint_requires_ops_auth(client, db_session):
    customer = make_customer(db_session)
    inquiry = make_inquiry(db_session, customer)
    db_session.commit()
    shipment_id = db_session.execute(
        select(m.Shipment).where(m.Shipment.inquiry_id == inquiry.id)
    ).scalar_one().id

    r = client.delete(f"/shipments/{shipment_id}")
    assert r.status_code == 401
