from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base
from models._mixins import TimestampMixin


class Customer(TimestampMixin, Base):
    """A Raaziq customer. Can have many inquiries and, once quotes are
    accepted, many shipments.

    `username`/`password_hash` are nullable: most customers never get a
    portal login (they're tracked by ops on their behalf). Ops grants
    access explicitly (`services.customers.grant_portal_access`) for
    higher-volume clients who want to self-serve; `portal_active` lets that
    access be revoked without clearing the username, so it can be
    re-enabled later without reissuing credentials.
    """

    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)

    username: Mapped[str | None] = mapped_column(String(60), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    portal_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    inquiries: Mapped[list["Inquiry"]] = relationship(back_populates="customer")  # noqa: F821
    shipments: Mapped[list["Shipment"]] = relationship(back_populates="customer")  # noqa: F821
