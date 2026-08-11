from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sqlalchemy import UniqueConstraint

from app.db import Base
from app.models._types import portable_enum
from app.models.enums import ShipmentStage, TransportMode


class Area(Base):
    """A department/team responsible for producing one operational stage
    (Documentation, Pickup, Transit, Customs, Arrival, Delivery, ...) for one
    transport mode. Any number of Workers can belong to the same Area —
    "anyone in Customs" is exactly "every Worker whose area_id points at the
    Customs area". `(stage, mode)` is unique: at most one Area owns a given
    stage within a given mode, so there is never ambiguity about who is
    responsible for advancing a shipment into it, and air/sea each get their
    own area (and worker queue) per stage even though both share the same
    `ShipmentStage` values.
    """

    __tablename__ = "area"
    __table_args__ = (UniqueConstraint("stage", "mode", name="uq_area_stage_mode"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    stage: Mapped[ShipmentStage] = mapped_column(portable_enum(ShipmentStage), nullable=False)
    mode: Mapped[TransportMode] = mapped_column(portable_enum(TransportMode), nullable=False)
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
