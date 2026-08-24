"""Owns job number allocation and shipment routing details. `allocate_job_number`
is the only place that touches `JobNumberCounter`, so the format and the
locking strategy live in one function.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_settings
from models.shipment import JobNumberCounter, Shipment
from utils.errors import NotFound, ShipmentHasInvoice


def _lock_counter_row(session: Session, year: int) -> JobNumberCounter | None:
    stmt = select(JobNumberCounter).where(JobNumberCounter.year == year)
    if session.bind.dialect.name == "postgresql":
        # SQLite has no SELECT ... FOR UPDATE; ordinary write serialization
        # is sufficient there. On PostgreSQL this blocks concurrent
        # allocations for the same year until the current transaction ends.
        stmt = stmt.with_for_update()
    return session.execute(stmt).scalar_one_or_none()


def allocate_job_number(session: Session, year: int) -> str:
    """Allocate the next job number for `year`, inside the caller's current
    transaction. Callers that need the allocation to roll back on later
    failure (e.g. quote acceptance) must not commit before that failure is
    resolved — the counter increment is not durable until the surrounding
    transaction commits.
    """
    settings = get_settings()
    counter = _lock_counter_row(session, year)
    if counter is None:
        counter = JobNumberCounter(year=year, last_value=0)
        session.add(counter)
        session.flush()

    counter.last_value += 1
    session.flush()

    sequence = str(counter.last_value).zfill(settings.job_number_padding)
    return f"{settings.job_number_prefix}-{year}-{sequence}"


def delete_shipment(session: Session, shipment_id: int) -> None:
    """Permanently removes a shipment and everything created solely for it
    (references, status events, documents, and every quote revision on its
    inquiry) -- for clearing out test/junk data, not a business operation.
    Real, in-progress shipments should be cancelled (`cancel_shipment`)
    instead, which keeps the audit trail; this erases it.

    Refuses outright if any quote on the inquiry has ever had an invoice
    (any status) -- an invoice is a financial record and must never
    disappear as a side effect of deleting the shipment it came from.
    """
    shipment = session.get(Shipment, shipment_id)
    if shipment is None:
        raise NotFound(f"Shipment {shipment_id} not found")

    inquiry = shipment.inquiry
    quotes = list(inquiry.quotes)
    if any(quote.invoices for quote in quotes):
        raise ShipmentHasInvoice(
            f"Shipment {shipment_id} has an invoice on one of its quotes and cannot be deleted; cancel it instead"
        )

    session.delete(shipment)
    for quote in quotes:
        session.delete(quote)
    session.delete(inquiry)
    session.flush()


def set_routing(
    session: Session, shipment: Shipment, *, carrier: str | None, voyage_flight_number: str | None
) -> Shipment:
    """Set the carrier and voyage/flight number, independent of stage --
    known once the job is booked, not before."""
    shipment.carrier = carrier
    shipment.voyage_flight_number = voyage_flight_number
    session.flush()
    return shipment
