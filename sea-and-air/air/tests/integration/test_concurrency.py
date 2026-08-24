"""Verifies the database constraints that are the *real* duplicate-prevention
mechanism for critical actions -- not the application-level checks in
services.quotes/services.invoices/services.shipments, which are a
clean-error-message layer on top, not the sole guard (see each service
module's own docstrings). These tests deliberately bypass the guarded
service functions and write directly through the ORM, proving the database
itself refuses the duplicate even if application logic somehow didn't catch
it first -- e.g. two near-simultaneous requests racing past the same
in-memory check on two different app server processes, which no amount of
frontend button-disabling can prevent.

True multi-connection threaded races against Postgres's `with_for_update()`
locks aren't exercised here: the test suite's SQLite engine uses a shared
StaticPool connection (see tests/conftest.py), so there's no separate
connection to race against, and SQLite doesn't take that lock in the first
place (see services.quotes.accept_quote's own comment on this). What's
verified instead is the constraint that would still catch the duplicate
even if the row lock were somehow bypassed or unavailable.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

import models as m
from models.enums import InvoiceStatus, QuoteStatus
from services.invoices import create_invoice_from_quote
from services.quotes import accept_quote, generate_quote
from factories import make_company, make_customer, make_inquiry, simple_rate_card

TODAY = date(2026, 6, 1)


def _accepted_quote(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    accept_quote(db_session, quote.id, "ops", today=TODAY)
    return quote


def test_database_rejects_a_second_active_invoice_for_the_same_quote(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)

    # Bypasses create_invoice_from_quote's own "already has an active
    # invoice" check entirely -- a raw second Invoice row for the same
    # quote_id, both status=ISSUED, is exactly what two racing requests
    # would each try to insert.
    duplicate = m.Invoice(
        invoice_number="INV-2026-DUPLICATE",
        quote_id=quote.id,
        shipment_id=quote.shipment.id,
        customer_id=quote.shipment.customer_id,
        company_id=company.id,
        status=InvoiceStatus.ISSUED,
        issued_date=TODAY,
        currency=quote.currency,
        subtotal=quote.subtotal,
        markup_amount=quote.markup_amount,
        total=quote.total,
        customer_name_snapshot="x",
        origin_snapshot="x",
        destination_snapshot="x",
        mode_snapshot="air",
        incoterm_snapshot="DAP",
        weight_kg_snapshot=Decimal("1"),
        volume_cbm_snapshot=Decimal("1"),
        chargeable_weight_kg_snapshot=Decimal("1"),
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_database_allows_a_second_invoice_once_the_first_is_cancelled(db_session):
    company = make_company(db_session)
    quote = _accepted_quote(db_session)
    original = create_invoice_from_quote(db_session, quote.id, company_id=company.id, today=TODAY)
    original.status = InvoiceStatus.CANCELLED
    db_session.flush()

    # Now permitted -- the partial unique index only covers non-cancelled rows.
    replacement = m.Invoice(
        invoice_number="INV-2026-REPLACEMENT",
        quote_id=quote.id,
        shipment_id=quote.shipment.id,
        customer_id=quote.shipment.customer_id,
        company_id=company.id,
        status=InvoiceStatus.ISSUED,
        issued_date=TODAY,
        currency=quote.currency,
        subtotal=quote.subtotal,
        markup_amount=quote.markup_amount,
        total=quote.total,
        customer_name_snapshot="x",
        origin_snapshot="x",
        destination_snapshot="x",
        mode_snapshot="air",
        incoterm_snapshot="DAP",
        weight_kg_snapshot=Decimal("1"),
        volume_cbm_snapshot=Decimal("1"),
        chargeable_weight_kg_snapshot=Decimal("1"),
    )
    db_session.add(replacement)
    db_session.flush()  # does not raise
    assert replacement.id is not None


def test_database_rejects_duplicate_invoice_numbers_regardless_of_quote(db_session):
    company = make_company(db_session)
    quote_a = _accepted_quote(db_session)
    quote_b = _accepted_quote(db_session)
    create_invoice_from_quote(db_session, quote_a.id, company_id=company.id, today=TODAY)

    duplicate_number = m.Invoice(
        invoice_number="INV-2026-00001",  # same number the first invoice got
        quote_id=quote_b.id,
        shipment_id=quote_b.shipment.id,
        customer_id=quote_b.shipment.customer_id,
        company_id=company.id,
        status=InvoiceStatus.ISSUED,
        issued_date=TODAY,
        currency=quote_b.currency,
        subtotal=quote_b.subtotal,
        markup_amount=quote_b.markup_amount,
        total=quote_b.total,
        customer_name_snapshot="x",
        origin_snapshot="x",
        destination_snapshot="x",
        mode_snapshot="air",
        incoterm_snapshot="DAP",
        weight_kg_snapshot=Decimal("1"),
        volume_cbm_snapshot=Decimal("1"),
        chargeable_weight_kg_snapshot=Decimal("1"),
    )
    db_session.add(duplicate_number)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_database_rejects_duplicate_job_numbers(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry_a = make_inquiry(db_session, customer)
    inquiry_b = make_inquiry(db_session, customer)
    quote_a = generate_quote(db_session, inquiry_a.id, today=TODAY)
    db_session.flush()
    shipment_a = accept_quote(db_session, quote_a.id, "ops", today=TODAY)

    # A second shipment claiming the same job_number a racing request also
    # allocated -- exactly what allocate_job_number's row lock prevents on
    # Postgres; this proves the fallback UNIQUE constraint would too.
    inquiry_b.shipment.job_number = shipment_a.job_number
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_database_rejects_a_second_shipment_pointing_at_the_same_accepted_quote(db_session):
    """Two jobs from the same accepted quote is exactly what Shipment.quote_id's
    own UNIQUE constraint (models.shipment.Shipment) rules out. Repoints an
    already-existing, unrelated shipment (every inquiry gets one
    automatically) rather than inserting a new row, so this isolates the
    quote_id constraint from Shipment.inquiry_id's own separate uniqueness.
    """
    quote = _accepted_quote(db_session)
    customer = make_customer(db_session)
    other_inquiry = make_inquiry(db_session, customer)

    other_inquiry.shipment.quote_id = quote.id
    with pytest.raises(IntegrityError):
        db_session.flush()
