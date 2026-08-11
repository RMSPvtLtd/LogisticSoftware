"""The customer-facing views of their own shipments/quotes/account. The
shipment list here is a lightweight summary (job number, route, stage, risk)
for the dashboard; shipment *detail* reuses `schemas.tracking.TrackingResult`
directly -- it's already the customer-safe shape (no pricing, no internal
notes, no risk_reason), so there's no reason to redeclare it. Quotes reuse
`schemas.quotes.QuoteRead` as-is, since a customer is allowed to see the full
pricing breakdown of their own quote.
"""

from datetime import datetime

from pydantic import BaseModel

from models.enums import ShipmentStage
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
    updated_at: datetime


def shipment_summary(shipment: Shipment) -> CustomerShipmentSummary:
    return CustomerShipmentSummary(
        id=shipment.id,
        job_number=shipment.job_number,
        origin=shipment.inquiry.origin,
        destination=shipment.inquiry.destination,
        stage=shipment.stage,
        is_at_risk=shipment.is_at_risk,
        updated_at=shipment.updated_at,
    )
