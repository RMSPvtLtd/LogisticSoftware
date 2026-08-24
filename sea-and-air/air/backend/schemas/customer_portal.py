"""The customer-facing views of their own shipments/quotes/invoices/account.
The shipment list here is a lightweight summary (job number, route, stage,
risk) for the dashboard; shipment *detail* reuses `schemas.tracking.
TrackingResult` directly -- it's already the customer-safe shape (no
pricing, no internal notes, no risk_reason), so there's no reason to
redeclare it. Quotes reuse `schemas.quotes.QuoteRead` as-is, since a customer
is allowed to see the full pricing breakdown of their own quote (supplier
info lives on Inquiry, which the customer portal never exposes directly, so
it was never reachable through the quote view either).

Invoices do NOT reuse `schemas.invoices.InvoiceRead` -- that schema includes
`supplier_name_snapshot`/`supplier_address_snapshot`, which must not
automatically reach a customer (a real freight-forwarder concern: revealing
the actual shipper lets a customer route around Raaziq directly) and
`cancelled_reason`, which is internal/audit-only. `CustomerInvoiceDetail` is
a hand-built, independent schema, the same pattern `schemas.tracking.
TrackingResult` already uses for the same reason.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from models.enums import ChargeKind, InvoiceStatus, ShipmentStage
from models.invoice import Invoice
from models.shipment import Shipment
from schemas.customers import CustomerRead


class CustomerLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer: CustomerRead


class CustomerShipmentSummary(BaseModel):
    id: int
    job_number: str | None
    origin: str
    destination: str
    stage: ShipmentStage
    is_at_risk: bool
    is_cancelled: bool
    is_on_hold: bool
    updated_at: datetime


def shipment_summary(shipment: Shipment) -> CustomerShipmentSummary:
    return CustomerShipmentSummary(
        id=shipment.id,
        job_number=shipment.job_number,
        origin=shipment.inquiry.origin,
        destination=shipment.inquiry.destination,
        stage=shipment.stage,
        is_at_risk=shipment.is_at_risk,
        is_cancelled=shipment.is_cancelled,
        is_on_hold=shipment.is_on_hold,
        updated_at=shipment.updated_at,
    )


class CustomerInvoiceLineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: ChargeKind
    description: str
    amount: Decimal


class CustomerInvoiceSummary(BaseModel):
    id: int
    invoice_number: str
    status: InvoiceStatus
    issued_date: date
    currency: str
    total: Decimal


class CustomerInvoiceDetail(BaseModel):
    id: int
    invoice_number: str
    status: InvoiceStatus
    issued_date: date
    currency: str
    subtotal: Decimal
    markup_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    origin: str
    destination: str
    incoterm: str
    job_number: str | None
    line_items: list[CustomerInvoiceLineItemRead]


def customer_invoice_summary(invoice: Invoice) -> CustomerInvoiceSummary:
    return CustomerInvoiceSummary(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        status=invoice.status,
        issued_date=invoice.issued_date,
        currency=invoice.currency,
        total=invoice.total,
    )


def customer_invoice_detail(invoice: Invoice) -> CustomerInvoiceDetail:
    return CustomerInvoiceDetail(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        status=invoice.status,
        issued_date=invoice.issued_date,
        currency=invoice.currency,
        subtotal=invoice.subtotal,
        markup_amount=invoice.markup_amount,
        tax_amount=invoice.tax_amount,
        discount_amount=invoice.discount_amount,
        total=invoice.total,
        origin=invoice.origin_snapshot,
        destination=invoice.destination_snapshot,
        incoterm=invoice.incoterm_snapshot,
        job_number=invoice.job_number_snapshot,
        line_items=[CustomerInvoiceLineItemRead.model_validate(li) for li in invoice.line_items],
    )
