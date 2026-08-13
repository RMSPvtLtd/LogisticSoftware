from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base
from models._types import portable_enum
from models.enums import ShipmentStage


class ShipmentDocument(Base):
    """A PDF ops optionally attaches to a shipment. Stored inline in
    Postgres (`data`, bytea) rather than external object storage — this
    deployment runs on Vercel serverless functions, which have no
    persistent disk, and a dedicated object-storage provider was
    deliberately deferred. `stage` is a snapshot of the shipment's stage at
    upload time; it is never updated afterward, even as the shipment
    progresses further.
    """

    __tablename__ = "shipment_document"

    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipment.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[ShipmentStage] = mapped_column(portable_enum(ShipmentStage), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    shipment: Mapped["Shipment"] = relationship(back_populates="documents")  # noqa: F821
