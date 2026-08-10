"""Owns job number allocation. `allocate_job_number` is the only place that
touches `JobNumberCounter`, so the format and the locking strategy live in
one function.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.shipment import JobNumberCounter


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
