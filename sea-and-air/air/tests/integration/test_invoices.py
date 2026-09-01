from datetime import date
from decimal import Decimal

import pytest

from utils.errors import InvalidCancellation, InvalidQuoteState, NotFound
from models.enums import ChargeKind, InvoiceStatus, ShipmentStage
from services.pdf_documents import render_invoice_pdf
from services.quotes import accept_quote, generate_quote
from services.invoices import cancel_invoice, create_invoice_from_quote
from services.transitions import advance_stage
from factories import add_charge, make_company, make_customer, make_inquiry, simple_rate_card

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
    assert invoice.cargo_type_snapshot == "General cargo"
    assert invoice.invoice_number.startswith("INV-2026-")
    assert len(invoice.line_items) == len(quote.line_items)


def test_create_invoice_from_quote_accepts_remarks(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)

    invoice = create_invoice_from_quote(
        db_session, quote.id, company_id=company.id, remarks="Handle with care", today=TODAY
    )

    assert invoice.remarks == "Handle with care"


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


def test_render_invoice_pdf_with_multiple_charge_kinds_does_not_raise(db_session):
    """The charges table groups line items by ChargeKind with a heading and
    subtotal per group -- exercise a real multi-kind invoice (freight +
    two accessory charges of different kinds) to catch a grouping bug that
    a single-kind fixture (_accepted_quote's default) wouldn't."""
    company = make_company(db_session)
    customer = make_customer(db_session)
    rate_card = simple_rate_card(db_session)
    add_charge(db_session, rate_card, kind=ChargeKind.DOCUMENTATION, description="Docs fee", amount=Decimal("45"))
    add_charge(db_session, rate_card, kind=ChargeKind.CUSTOMS, description="Customs clearance", amount=Decimal("30"))
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    accept_quote(db_session, quote.id, "ops", today=TODAY)
    invoice = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)

    kinds_present = {li.kind for li in invoice.line_items}
    assert len(kinds_present) >= 2

    pdf_bytes = render_invoice_pdf(invoice)

    assert pdf_bytes[:4] == b"%PDF"


# --- cancellation + replacement ---


def test_cancel_invoice_sets_status_and_audit_fields(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    invoice = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)

    cancelled = cancel_invoice(db_session, invoice.id, reason="Duplicate billing", actor="ops")

    assert cancelled.status == InvoiceStatus.CANCELLED
    assert cancelled.cancelled_reason == "Duplicate billing"
    assert cancelled.cancelled_by == "ops"
    assert cancelled.cancelled_at is not None


def test_cancel_invoice_requires_a_reason(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    invoice = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)

    with pytest.raises(InvalidCancellation):
        cancel_invoice(db_session, invoice.id, reason=" ", actor="ops")


def test_cannot_cancel_an_already_cancelled_invoice(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    invoice = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)
    cancel_invoice(db_session, invoice.id, reason="First", actor="ops")

    with pytest.raises(InvalidCancellation):
        cancel_invoice(db_session, invoice.id, reason="Second", actor="ops")


def test_cancellation_does_not_touch_financial_fields(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    invoice = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)
    original_total, original_lines = invoice.total, len(invoice.line_items)

    cancel_invoice(db_session, invoice.id, reason="Duplicate billing", actor="ops")

    assert invoice.total == original_total
    assert len(invoice.line_items) == original_lines
    # PDF generation still succeeds and reads the same, unmodified fields.
    assert render_invoice_pdf(invoice)[:4] == b"%PDF"


def test_replacement_invoice_can_be_created_after_cancellation(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    original = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)
    cancel_invoice(db_session, original.id, reason="Wrong company billed", actor="ops")

    replacement = create_invoice_from_quote(
        db_session, quote.id, company_id=company.id, replaces_invoice_id=original.id, today=TODAY,
    )

    assert replacement.id != original.id
    assert replacement.invoice_number != original.invoice_number
    assert replacement.replaces_invoice_id == original.id
    assert quote.active_invoice.id == replacement.id


def test_cannot_create_a_second_active_invoice_without_cancelling_the_first(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    original = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)

    with pytest.raises(InvalidQuoteState):
        create_invoice_from_quote(
            db_session, quote.id, company_id=company.id, replaces_invoice_id=original.id, today=TODAY,
        )


def test_replaces_invoice_id_must_reference_a_cancelled_invoice_on_the_same_quote(db_session):
    company = make_company(db_session)
    quote_a = _accepted_quote(db_session)
    quote_b = _accepted_quote(db_session)
    invoice_a = create_invoice_from_quote(db_session, quote_a.id, company_id=company.id, today=TODAY)

    with pytest.raises(NotFound):
        # invoice_a belongs to quote_a, not quote_b.
        create_invoice_from_quote(
            db_session, quote_b.id, company_id=company.id, replaces_invoice_id=invoice_a.id, today=TODAY,
        )


def test_invoice_number_is_never_reused(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    original = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)
    cancel_invoice(db_session, original.id, reason="Correction needed", actor="ops")
    replacement = create_invoice_from_quote(
        db_session, quote.id, company_id=company.id, replaces_invoice_id=original.id, today=TODAY,
    )

    assert original.invoice_number != replacement.invoice_number
    assert replacement.invoice_number == "INV-2026-00002"


def test_cancel_invoice_endpoint(client, db_session, ops_headers):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    invoice = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)
    db_session.commit()

    r = client.post(f"/invoices/{invoice.id}/cancel", json={"reason": "Issued in error"}, headers=ops_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"
    assert r.json()["cancelled_reason"] == "Issued in error"

    # Cancelled invoices remain permanently visible, not deleted.
    r = client.get(f"/invoices/{invoice.id}", headers=ops_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"

    r = client.get("/invoices", headers=ops_headers)
    assert any(i["id"] == invoice.id for i in r.json())


def test_invoice_upload_endpoint(client, db_session, ops_headers):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    db_session.commit()

    r = client.post(f"/quotes/{quote.id}/invoice", json={"company_id": company.id}, headers=ops_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["quote_id"] == quote.id
    invoice_id = body["id"]

    r = client.get(f"/invoices/{invoice_id}", headers=ops_headers)
    assert r.status_code == 200, r.text

    r = client.get(f"/quotes/{quote.id}", headers=ops_headers)
    assert r.json()["invoice_id"] == invoice_id

    # Duplicate creation is rejected.
    r = client.post(f"/quotes/{quote.id}/invoice", json={"company_id": company.id}, headers=ops_headers)
    assert r.status_code == 409, r.text

    r = client.get(f"/invoices/{invoice_id}/pdf", headers=ops_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


def test_quote_pdf_endpoint(client, db_session, ops_headers):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    db_session.commit()

    r = client.get(f"/quotes/{quote.id}/pdf", headers=ops_headers)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
