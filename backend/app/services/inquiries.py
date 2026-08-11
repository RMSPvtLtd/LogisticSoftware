"""Owns Inquiry creation. The one thing this module adds beyond a plain
insert: every Inquiry gets a Shipment tracking row in the same transaction,
starting at the INQUIRY stage. That row is what makes a job trackable (by
staff, workers, and eventually the customer) from the moment it's filed,
long before a quote exists or is accepted — accepting a quote now advances
this same row rather than creating a new one (see
`services.quotes.accept_quote`).
"""

from sqlalchemy.orm import Session

from app.errors import NotFound
from app.models.customer import Customer
from app.models.enums import EventSource, ShipmentStage
from app.models.inquiry import Inquiry
from app.models.shipment import Shipment, StatusEvent
from app.schemas.inquiries import InquiryCreate


def create_inquiry(session: Session, payload: InquiryCreate) -> Inquiry:
    if session.get(Customer, payload.customer_id) is None:
        raise NotFound(f"Customer {payload.customer_id} not found")

    inquiry = Inquiry(**payload.model_dump())
    session.add(inquiry)
    session.flush()  # assigns inquiry.id

    shipment = Shipment(customer_id=inquiry.customer_id, inquiry_id=inquiry.id, stage=ShipmentStage.INQUIRY)
    session.add(shipment)
    session.flush()
    shipment.status_events.append(
        StatusEvent(
            stage=ShipmentStage.INQUIRY,
            actor="system",
            note="Inquiry received.",
            source=EventSource.SYSTEM,
            is_stage_change=True,
        )
    )
    session.flush()

    return inquiry
