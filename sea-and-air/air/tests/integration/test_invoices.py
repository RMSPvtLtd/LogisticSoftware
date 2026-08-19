from datetime import date

import pytest

from utils.errors import InvalidQuoteState, NotFound
from models.enums import ShipmentStage
from services.pdf_documents import render_invoice_pdf
from services.quotes import accept_quote, generate_quote
from services.invoices import create_invoice_from_quote
from services.transitions import advance_stage
from factories import make_company, make_customer, make_inquiry, simple_rate_card

TODAY = date(2026, 6, 1)


def _accepted_quote(db_session, **inquiry_overrides):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer, **inquiry_overrides)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    accept_quote(db_session, quote.id, "ops", today=TODAY)
    return quote


def test_create_invoice_from_accepted_quote(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(
        db_session, hs_code="1234.56", pieces=5,
        supplier_name="Test Supplier Ltd", supplier_address="1 Supplier Road",
    )

    invoice = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)

    assert invoice.quote_id == quote.id
    assert invoice.company_id == company.id
    assert invoice.total == quote.total
    assert invoice.currency == quote.currency
    assert invoice.hs_code_snapshot == "1234.56"
    assert invoice.pieces_snapshot == 5
    assert invoice.supplier_name_snapshot == "Test Supplier Ltd"
    assert invoice.invoice_number.startswith("INV-2026-")
    assert len(invoice.line_items) == len(quote.line_items)


def test_create_invoice_rejected_for_non_accepted_quote(db_session):
    company = make_company(db_session)
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)  # never accepted
    db_session.flush()

    with pytest.raises(InvalidQuoteState):
        create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)


def test_create_invoice_rejected_when_already_invoiced(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)

    with pytest.raises(InvalidQuoteState):
        create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)


def test_create_invoice_missing_company_raises_not_found(db_session):
    quote = _accepted_quote(db_session)
    with pytest.raises(NotFound):
        create_invoice_from_quote(db_session, quote.id, company_id=999999, today=TODAY)


def test_invoice_numbers_are_sequential_and_unique(db_session):
    company = make_company(db_session)
    quote_a = _accepted_quote(db_session)
    quote_b = _accepted_quote(db_session)

    invoice_a = create_invoice_from_quote(db_session, quote_a.id, company_id=company.id, today=TODAY)
    invoice_b = create_invoice_from_quote(db_session, quote_b.id, company_id=company.id, today=TODAY)

    assert invoice_a.invoice_number == "INV-2026-00001"
    assert invoice_b.invoice_number == "INV-2026-00002"


def test_invoice_is_a_snapshot_independent_of_later_quote_edits(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session, supplier_name="Original Supplier")

    invoice = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)
    original_total = invoice.total
    original_supplier = invoice.supplier_name_snapshot

    # Advance the shipment PAST invoicing isn't needed here -- what matters
    # is that editing the inquiry/quote after invoice creation never touches
    # the already-created invoice's snapshot.
    quote.inquiry.supplier_name = "Changed Supplier"
    quote.subtotal = quote.subtotal + 500
    quote.total = quote.total + 500
    db_session.flush()

    db_session.refresh(invoice)
    assert invoice.total == original_total
    assert invoice.supplier_name_snapshot == original_supplier


def test_quote_edit_blocked_after_invoiced_shipment_reaches_terminal_stage(db_session):
    from models.enums import EventSource, OPERATIONAL_STAGE_ORDER
    from services.quotes import override_line_items, LineItemOverride
    from decimal import Decimal

    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    shipment = quote.shipment
    start = OPERATIONAL_STAGE_ORDER.index(ShipmentStage.JOB_OPENING) + 1
    for stage in OPERATIONAL_STAGE_ORDER[start:]:
        advance_stage(db_session, shipment, stage, actor="ops", note=None, source=EventSource.MANUAL)
    assert shipment.stage == ShipmentStage.INVOICE_TO_CUSTOMER

    line_item_id = quote.line_items[0].id
    with pytest.raises(InvalidQuoteState):
        override_line_items(db_session, quote.id, [LineItemOverride(line_item_id, Decimal("1"))], today=TODAY)

    # An invoice can still be generated from the accepted quote even once
    # the shipment has reached its terminal stage -- editing is what's
    # blocked, not invoicing.
    invoice = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)
    assert invoice.id is not None


def test_render_invoice_pdf_returns_valid_pdf_bytes(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    invoice = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)

    pdf_bytes = render_invoice_pdf(invoice)

    assert pdf_bytes[:4] == b"%PDF"


def test_invoice_upload_endpoint(client, db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    db_session.commit()

    r = client.post(f"/quotes/{quote.id}/invoice", json={"company_id": company.id})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["quote_id"] == quote.id
    invoice_id = body["id"]

    r = client.get(f"/invoices/{invoice_id}")
    assert r.status_code == 200, r.text

    r = client.get(f"/quotes/{quote.id}")
    assert r.json()["invoice_id"] == invoice_id

    # Duplicate creation is rejected.
    r = client.post(f"/quotes/{quote.id}/invoice", json={"company_id": company.id})
    assert r.status_code == 409, r.text

    r = client.get(f"/invoices/{invoice_id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


def test_quote_pdf_endpoint(client, db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    db_session.commit()

    r = client.get(f"/quotes/{quote.id}/pdf")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
