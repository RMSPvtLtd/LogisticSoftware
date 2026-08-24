"""Metadata-only document schema -- deliberately excludes the PDF bytes
themselves, the same separation `schemas/tracking.py` keeps from
`schemas/shipments.py`: list/read responses stay small, and the binary
content is only ever served by the dedicated download route.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.enums import DocumentType, ShipmentStage


class ShipmentDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    stage: ShipmentStage
    document_type: DocumentType
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by: str
    created_at: datetime
