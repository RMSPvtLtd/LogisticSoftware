from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from models.enums import ChargeKind, InvoiceStatus


class InvoiceLineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: ChargeKind
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str
    quote_id: int
    shipment_id: int
    customer_id: int
    company_id: int
    status: InvoiceStatus
    issued_date: date
    currency: str
    subtotal: Decimal
    markup_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    customer_name_snapshot: str
    customer_address_snapshot: str | None
    supplier_name_snapshot: str | None
    supplier_address_snapshot: str | None
    origin_snapshot: str
    destination_snapshot: str
    mode_snapshot: str
    incoterm_snapshot: str
    hs_code_snapshot: str | None
    pieces_snapshot: int | None
    weight_kg_snapshot: Decimal
    volume_cbm_snapshot: Decimal
    chargeable_weight_kg_snapshot: Decimal
    carrier_snapshot: str | None
    voyage_flight_number_snapshot: str | None
    job_number_snapshot: str | None
    created_at: datetime
    line_items: list[InvoiceLineItemRead]


class InvoiceCreateRequest(BaseModel):
    company_id: int
