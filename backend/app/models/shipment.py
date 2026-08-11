from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixins import TimestampMixin
from app.models._types import portable_enum
from app.models.enums import EventSource, ReferenceType, ShipmentStage, TransportMode


class Shipment(TimestampMixin, Base):
    """The tracking record for one job, created the moment an Inquiry is
    filed (`services.inquiries.create_inquiry`) — not when a quote is
    accepted. `quote_id` is set once a quote is generated (and re-pointed if
    the inquiry is re-quoted) and `job_number` is only assigned once that
    quote is accepted, both nullable until then; each is UNIQUE when
    present. `stage` is written only by `services.transitions` (or the
    quote-lifecycle functions that call into it for the two system-driven
    transitions before job_opening).

    `mode` is a denormalized copy of `inquiry.mode`, set once at creation and
    never changed after — it exists so mode-aware queries (the worker queue,
    the tracking checklist labels) don't need a join through Inquiry on
    every read. Inquiry.mode remains the source of truth; this column is
    always in sync with it because both are written together in
    `services.inquiries.create_inquiry`.
    """

    __tablename__ = "shipment"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), nullable=False, index=True)
    inquiry_id: Mapped[int] = mapped_column(ForeignKey("inquiry.id"), nullable=False, unique=True)
    quote_id: Mapped[int | None] = mapped_column(ForeignKey("quote.id"), unique=True)

    mode: Mapped[TransportMode] = mapped_column(portable_enum(TransportMode), nullable=False)
    job_number: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)
    stage: Mapped[ShipmentStage] = mapped_column(
        portable_enum(ShipmentStage), nullable=False, default=ShipmentStage.INQUIRY
    )
    is_at_risk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_reason: Mapped[str | None] = mapped_column(Text)

    customer: Mapped["Customer"] = relationship(back_populates="shipments")  # noqa: F821
    inquiry: Mapped["Inquiry"] = relationship(back_populates="shipment")  # noqa: F821
    quote: Mapped["Quote | None"] = relationship(back_populates="shipment")  # noqa: F821
    references: Mapped[list["ShipmentReference"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan"
    )
    status_events: Mapped[list["StatusEvent"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan", order_by="StatusEvent.timestamp"
    )


class ShipmentReference(Base):
    """A searchable reference number attached to a shipment (job number,
    MAWB, HAWB, MBL, HBL, container, ...). Kept in its own table rather than
    fixed columns on Shipment so new reference types can be added without a
    schema change. Uniqueness is scoped to (shipment_id, type, value), not
    globally, because a container or job number can legitimately recur
    across unrelated shipments over time; the tracking lookup handles that
    possibility explicitly instead of relying on a global constraint.
    """

    __tablename__ = "shipment_reference"
    __table_args__ = (
        UniqueConstraint("shipment_id", "type", "value", name="uq_shipment_reference_shipment_type_value"),
        Index("ix_shipment_reference_value", "value"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipment.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[ReferenceType] = mapped_column(portable_enum(ReferenceType), nullable=False)
    value: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    shipment: Mapped["Shipment"] = relationship(back_populates="references")


class StatusEvent(Base):
    """An append-only record of one moment in a shipment's history: either a
    real stage transition (`is_stage_change=True`) or a note/annotation at
    the current stage. No API updates or deletes a row in this table —
    corrections are always new rows (see `services.transitions.correct_stage`).

    `source` is always assigned by the server-side operation that created the
    event, never accepted from a request body, because it is part of the
    audit trail: manual status update -> manual, correction endpoint ->
    correction, quote acceptance / system risk notes -> system, tracking
    adapter ingestion -> automated.

    `is_internal` marks notes that must never reach the customer-safe
    tracking endpoint (e.g. internal ops commentary), so filtering what the
    public API returns is a flag check, not a convention.
    """

    __tablename__ = "status_event"
    __table_args__ = (Index("ix_status_event_shipment_timestamp", "shipment_id", "timestamp"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipment.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[ShipmentStage] = mapped_column(portable_enum(ShipmentStage), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    source: Mapped[EventSource] = mapped_column(portable_enum(EventSource), nullable=False)
    is_stage_change: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    shipment: Mapped["Shipment"] = relationship(back_populates="status_events")


class JobNumberCounter(Base):
    """Row-locked allocator for human-readable job numbers, one row per year.
    Kept as a plain counter table (rather than a PostgreSQL sequence) so the
    same allocation code works unchanged on the SQLite test database.
    """

    __tablename__ = "job_number_counter"

    year: Mapped[int] = mapped_column(primary_key=True)
    last_value: Mapped[int] = mapped_column(nullable=False, default=0)
