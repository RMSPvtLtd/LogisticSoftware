from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixins import TimestampMixin
from app.models._types import portable_enum
from app.models.enums import ChargeKind, QuoteStatus


class Quote(TimestampMixin, Base):
    """A priced quotation for one Inquiry. Totals are always derived from its
    QuoteLineItems by `services.quotes.recalculate_totals` — this table never
    stores a total that wasn't computed from line items.
    """

    __tablename__ = "quote"

    id: Mapped[int] = mapped_column(primary_key=True)
    inquiry_id: Mapped[int] = mapped_column(ForeignKey("inquiry.id"), nullable=False, index=True)

    status: Mapped[QuoteStatus] = mapped_column(
        portable_enum(QuoteStatus), nullable=False, default=QuoteStatus.DRAFT
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    markup_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)

    inquiry: Mapped["Inquiry"] = relationship(back_populates="quotes")  # noqa: F821
    line_items: Mapped[list["QuoteLineItem"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan", order_by="QuoteLineItem.id"
    )
    shipment: Mapped["Shipment | None"] = relationship(back_populates="quote", uselist=False)  # noqa: F821


class QuoteLineItem(Base):
    """One priced component of a quote (freight, documentation, customs, ...).
    `calculated_total` is what the pricing engine produced and is never
    modified afterward. `final_total` is what the quote actually charges —
    equal to `calculated_total` unless a pricing user overrides it, in which
    case `is_manual_override` is set. `recalculate_totals` treats
    `final_total` as authoritative when an override exists, `calculated_total`
    otherwise.
    """

    __tablename__ = "quote_line_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quote.id", ondelete="CASCADE"), nullable=False, index=True)

    kind: Mapped[ChargeKind] = mapped_column(portable_enum(ChargeKind), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    calculated_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    final_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    markup_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    is_manual_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    quote: Mapped["Quote"] = relationship(back_populates="line_items")
