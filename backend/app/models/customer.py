from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixins import TimestampMixin


class Customer(TimestampMixin, Base):
    """A Raaziq customer. Can have many inquiries and, once quotes are
    accepted, many shipments.
    """

    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50))

    inquiries: Mapped[list["Inquiry"]] = relationship(back_populates="customer")  # noqa: F821
    shipments: Mapped[list["Shipment"]] = relationship(back_populates="customer")  # noqa: F821
