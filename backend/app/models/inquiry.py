from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixins import TimestampMixin
from app.models._types import portable_enum
from app.models.enums import TransportMode


class Inquiry(TimestampMixin, Base):
    """A customer's initial freight request — the information the pricing
    engine needs to produce a quote.
    """

    __tablename__ = "inquiry"
    __table_args__ = (Index("ix_inquiry_lane_mode", "origin", "destination", "mode"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), nullable=False, index=True)

    origin: Mapped[str] = mapped_column(String(120), nullable=False)
    destination: Mapped[str] = mapped_column(String(120), nullable=False)
    mode: Mapped[TransportMode] = mapped_column(portable_enum(TransportMode), nullable=False)
    cargo_type: Mapped[str] = mapped_column(String(120), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    volume_cbm: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    dimensions: Mapped[str | None] = mapped_column(String(200))
    ready_date: Mapped[date | None] = mapped_column(Date)
    incoterm: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    customer: Mapped["Customer"] = relationship(back_populates="inquiries")  # noqa: F821
    quotes: Mapped[list["Quote"]] = relationship(back_populates="inquiry")  # noqa: F821
    shipment: Mapped["Shipment | None"] = relationship(back_populates="inquiry", uselist=False)  # noqa: F821
