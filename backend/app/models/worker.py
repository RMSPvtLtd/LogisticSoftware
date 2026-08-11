from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._types import portable_enum
from app.models.enums import ShipmentStage


class Area(Base):
    """A department/team responsible for producing one operational stage
    (Documentation, Pickup, Transit, Customs, Arrival, Delivery, ...). Any
    number of Workers can belong to the same Area — "anyone in Customs" is
    exactly "every Worker whose area_id points at the Customs area". `stage`
    is unique: at most one Area owns a given stage, so there is never
    ambiguity about who is responsible for advancing a shipment into it.
    """

    __tablename__ = "area"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    stage: Mapped[ShipmentStage] = mapped_column(portable_enum(ShipmentStage), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    workers: Mapped[list["Worker"]] = relationship(back_populates="area")


class Worker(Base):
    """A warehouse/ops staff account scoped to exactly one Area. A worker can
    only see and act on shipments waiting at their area's stage — enforced
    in `app.security` (token → worker) and `app.api.worker_portal` (worker's
    area.stage must be the shipment's next stage), not left to the frontend.
    """

    __tablename__ = "worker"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    area_id: Mapped[int] = mapped_column(ForeignKey("area.id"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    area: Mapped["Area"] = relationship(back_populates="workers")
