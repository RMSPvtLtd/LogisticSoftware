"""The worker-facing view of a shipment queue item. Independent of
`schemas/shipments.py` (the ops-facing schema) for the same reason
`schemas/tracking.py` is independent of it: a worker's queue has no reason
to carry quote/customer-account internals, so nothing here is inherited
from a schema that does.
"""

from datetime import datetime

from pydantic import BaseModel

from models.shipment import Shipment


class WorkerQueueItem(BaseModel):
    id: int
    # Null whenever a shipment reached this stage via a stage correction
    # rather than the normal accept_quote flow (job numbers are only
    # allocated on quote acceptance) -- a worker's queue must still render
    # such a shipment rather than 500ing on it.
    job_number: str | None
    customer_name: str
    origin: str
    destination: str
    cargo_type: str
    waiting_since: datetime
    last_note: str | None


class CompleteStageRequest(BaseModel):
    note: str | None = None


def from_shipment(shipment: Shipment) -> WorkerQueueItem:
    last_event = shipment.status_events[-1] if shipment.status_events else None
    return WorkerQueueItem(
        id=shipment.id,
        job_number=shipment.job_number,
        customer_name=shipment.customer.name,
        origin=shipment.inquiry.origin,
        destination=shipment.inquiry.destination,
        cargo_type=shipment.inquiry.cargo_type,
        waiting_since=shipment.updated_at,
        last_note=last_event.note if last_event else None,
    )
