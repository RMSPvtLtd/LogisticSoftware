from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixins import TimestampMixin
from app.models._types import portable_enum
from app.models.enums import ChargeBasis, ChargeKind, TransportMode, UnitOfMeasure


class RateCard(TimestampMixin, Base):
    """Reusable freight pricing for one lane/mode/carrier over a validity
    window. `RateCardBreak` rows (below) hold the actual weight/volume-based
    pricing; `RateCardCharge` rows hold the accessory fees (documentation,
    customs, pickup, ...) — both as data, not as logic in the pricing engine.
    """

    __tablename__ = "rate_card"
    __table_args__ = (
        Index("ix_rate_card_lane_mode_validity", "origin", "destination", "mode", "valid_from", "valid_until"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    origin: Mapped[str] = mapped_column(String(120), nullable=False)
    destination: Mapped[str] = mapped_column(String(120), nullable=False)
    mode: Mapped[TransportMode] = mapped_column(portable_enum(TransportMode), nullable=False)
    carrier: Mapped[str | None] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    minimum_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    breaks: Mapped[list["RateCardBreak"]] = relationship(
        back_populates="rate_card", cascade="all, delete-orphan"
    )
    charges: Mapped[list["RateCardCharge"]] = relationship(
        back_populates="rate_card", cascade="all, delete-orphan"
    )


class RateCardBreak(Base):
    """One weight/volume pricing tier of a rate card.

    Bounds are half-open: [min, max) — the lower bound is inclusive, the upper
    bound exclusive, except the open-ended final break (max is NULL), which
    extends to infinity. A NULL bound on a given dimension means that
    dimension imposes no restriction; if both weight and volume bounds are
    set, a break only matches when both are satisfied.
    """

    __tablename__ = "rate_card_break"
    __table_args__ = (
        CheckConstraint("max_weight IS NULL OR max_weight > min_weight", name="ck_break_weight_range"),
        CheckConstraint("max_volume IS NULL OR max_volume > min_volume", name="ck_break_volume_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rate_card_id: Mapped[int] = mapped_column(
        ForeignKey("rate_card.id", ondelete="CASCADE"), nullable=False, index=True
    )

    min_weight: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    max_weight: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    min_volume: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    max_volume: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))

    unit: Mapped[UnitOfMeasure] = mapped_column(portable_enum(UnitOfMeasure), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200))

    rate_card: Mapped["RateCard"] = relationship(back_populates="breaks")


class RateCardCharge(Base):
    """An accessory fee attached to a rate card (documentation, customs,
    pickup, handling, ...). `amount` is interpreted per `basis`:
    flat -> the amount itself; per_kg -> amount * chargeable weight;
    percent_of_freight -> amount is a whole percent of the freight charge
    (amount=5.00 means 5%), so charge = freight * amount / 100.
    """

    __tablename__ = "rate_card_charge"

    id: Mapped[int] = mapped_column(primary_key=True)
    rate_card_id: Mapped[int] = mapped_column(
        ForeignKey("rate_card.id", ondelete="CASCADE"), nullable=False, index=True
    )

    kind: Mapped[ChargeKind] = mapped_column(portable_enum(ChargeKind), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    basis: Mapped[ChargeBasis] = mapped_column(portable_enum(ChargeBasis), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    rate_card: Mapped["RateCard"] = relationship(back_populates="charges")
