from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db import Base
from models._mixins import TimestampMixin
from models._types import portable_enum
from models.enums import TransportMode


class AirlineSchedule(TimestampMixin, Base):
    """A reference-only record of which days of the week an airline flies a
    given lane. Ops-facing information only -- nothing in the pricing or
    quoting engine reads this table; it exists purely so ops can look up
    "does PIA fly LHE->LHR on a Wednesday" while planning a shipment.
    """

    __tablename__ = "airline_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    airline_name: Mapped[str] = mapped_column(String(120), nullable=False)
    origin: Mapped[str] = mapped_column(String(120), nullable=False)
    destination: Mapped[str] = mapped_column(String(120), nullable=False)
    mode: Mapped[TransportMode] = mapped_column(portable_enum(TransportMode), nullable=False)
    # JSON-encoded list of day codes, e.g. '["mon","wed","fri"]' -- same
    # convention as Invoice.references_snapshot: a Text column keeps this
    # portable between SQLite (tests) and PostgreSQL (production) without
    # relying on a native array/JSON column type.
    days_of_week: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
