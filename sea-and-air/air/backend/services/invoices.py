"""Turns an accepted Quote into a durable, independent financial record.
`allocate_invoice_number` is the only place that touches
`InvoiceNumberCounter` (mirrors `services.shipments.allocate_job_number`
exactly). `create_invoice_from_quote` is the only writer of `Invoice` and
`InvoiceLineItem` -- everything it copies from the quote/inquiry/shipment/
customer is snapshotted at that moment and never re-read from those tables
again, so editing any of them afterward can't retroactively change a
historical invoice (see `models.invoice.Invoice`'s docstring).
"""

import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_settings
from utils.errors import InvalidQuoteState, NotFound
from models.enums import QuoteStatus
from models.invoice import Invoice, InvoiceLineItem, InvoiceNumberCounter
from models.quote import Quote
from services.companies import get_company
from services.pricing import compute_chargeable_weight


def _lock_counter_row(session: Session, year: int) -> InvoiceNumberCounter | None:
    stmt = select(InvoiceNumberCounter).where(InvoiceNumberCounter.year == year)
    if session.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    return session.execute(stmt).scalar_one_or_none()


def allocate_invoice_number(session: Session, year: int) -> str:
    settings = get_settings()
    counter = _lock_counter_row(session, year)
    if counter is None:
        counter = InvoiceNumberCounter(year=year, last_value=0)
        session.add(counter)
        session.flush()

    counter.last_value += 1
    session.flush()

    sequence = str(counter.last_value).zfill(settings.invoice_number_padding)
    return f"{settings.invoice_number_prefix}-{year}-{sequence}"


def create_invoice_from_quote(
    session: Session, quote_id: int, *, company_id: int, today: date | None = None
) -> Invoice:
    today = today or date.today()
    settings = get_settings()

    quote = session.get(Quote, quote_id)
    if quote is None:
        raise NotFound(f"Quote {quote_id} not found")
    if quote.status != QuoteStatus.ACCEPTED:
        raise InvalidQuoteState(f"Quote {quote.id} must be accepted before an invoice can be created (status={quote.status.value})")
    if quote.invoice is not None:
        # Also enforced at the database level by invoice.quote_id's UNIQUE
        # constraint -- this check just gives a clean, specific error instead
        # of a generic integrity-conflict one on the (rare) race.
        raise InvalidQuoteState(f"Quote {quote.id} already has an invoice ({quote.invoice.invoice_number})")

    shipment = quote.shipment
    if shipment is None:
        raise NotFound(f"Quote {quote.id} has no shipment to invoice")
    inquiry = quote.inquiry
    customer = shipment.customer

    company = get_company(session, company_id)

    references_snapshot = json.dumps(
        [{"type": ref.type.value, "value": ref.value} for ref in shipment.references]
    )

    invoice = Invoice(
        invoice_number=allocate_invoice_number(session, today.year),
        quote=quote,  # sets quote_id via the relationship (not the raw FK)
        # so quote.invoice is kept in sync at the Python object level too --
        # a plain quote_id=quote.id wouldn't populate the back_populates side,
        # leaving a stale quote.invoice=None for the rest of this session.
        shipment_id=shipment.id,
        customer_id=customer.id,
        company_id=company.id,
        issued_date=today,
        currency=quote.currency,
        subtotal=quote.subtotal,
        markup_amount=quote.markup_amount,
        tax_amount=quote.tax_amount,
        discount_amount=quote.discount_amount,
        total=quote.total,
        customer_name_snapshot=customer.name,
        customer_address_snapshot=customer.address,
        supplier_name_snapshot=inquiry.supplier_name,
        supplier_address_snapshot=inquiry.supplier_address,
        origin_snapshot=inquiry.origin,
        destination_snapshot=inquiry.destination,
        mode_snapshot=inquiry.mode.value,
        incoterm_snapshot=inquiry.incoterm,
        hs_code_snapshot=inquiry.hs_code,
        pieces_snapshot=inquiry.pieces,
        weight_kg_snapshot=inquiry.weight_kg,
        volume_cbm_snapshot=inquiry.volume_cbm,
        chargeable_weight_kg_snapshot=compute_chargeable_weight(inquiry, settings),
        carrier_snapshot=shipment.carrier,
        voyage_flight_number_snapshot=shipment.voyage_flight_number,
        job_number_snapshot=shipment.job_number,
        references_snapshot=references_snapshot,
    )
    # Added to the session before appending line items / setting the
    # quote<->invoice back-populate, so autoflush doesn't warn about a
    # transient object being referenced mid-construction.
    session.add(invoice)
    for line in quote.line_items:
        invoice.line_items.append(
            InvoiceLineItem(
                kind=line.kind,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                amount=line.final_total,
            )
        )

    session.flush()
    return invoice


def get_invoice(session: Session, invoice_id: int) -> Invoice:
    invoice = session.get(Invoice, invoice_id)
    if invoice is None:
        raise NotFound(f"Invoice {invoice_id} not found")
    return invoice


def list_invoices(session: Session) -> list[Invoice]:
    return list(session.execute(select(Invoice).order_by(Invoice.id)).scalars())
