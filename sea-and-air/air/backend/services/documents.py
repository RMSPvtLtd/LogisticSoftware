"""Owns validation and storage of PDF attachments on a Shipment. PDFs are
stored inline in Postgres (see `models.document.ShipmentDocument`) -- a
deliberate choice for this deployment (Vercel serverless has no persistent
disk), not a stopgap. Validation lives here rather than in a Pydantic schema
because `UploadFile`/`File()` multipart params aren't schema fields, and
this keeps the check usable outside a request (tests) same as every other
service in this package.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from utils.errors import InvalidDocument, NotFound
from models.document import ShipmentDocument
from models.shipment import Shipment

# Vercel Functions enforce a hard 4.5 MB request-body cap platform-wide
# (regardless of plan) -- requests over that never reach handler code at
# all. 4 MB leaves headroom for multipart boundary/header overhead.
MAX_DOCUMENT_SIZE_BYTES = 4 * 1024 * 1024
ALLOWED_CONTENT_TYPE = "application/pdf"
PDF_MAGIC = b"%PDF-"


def upload_document(
    session: Session,
    shipment: Shipment,
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
    actor: str,
) -> ShipmentDocument:
    if content_type != ALLOWED_CONTENT_TYPE:
        raise InvalidDocument(f"Only PDF uploads are allowed (got {content_type!r})")
    if not data:
        raise InvalidDocument("Uploaded file is empty")
    if not data.startswith(PDF_MAGIC):
        raise InvalidDocument("File does not look like a valid PDF")
    if len(data) > MAX_DOCUMENT_SIZE_BYTES:
        raise InvalidDocument(f"File exceeds the {MAX_DOCUMENT_SIZE_BYTES // (1024 * 1024)} MB upload limit")

    document = ShipmentDocument(
        shipment_id=shipment.id,
        stage=shipment.stage,
        filename=filename or "document.pdf",
        content_type=content_type,
        size_bytes=len(data),
        data=data,
        uploaded_by=actor,
    )
    session.add(document)
    session.flush()
    return document


def list_documents(session: Session, shipment_id: int) -> list[ShipmentDocument]:
    stmt = (
        select(ShipmentDocument)
        .where(ShipmentDocument.shipment_id == shipment_id)
        .order_by(ShipmentDocument.created_at)
    )
    return list(session.execute(stmt).scalars())


def get_document(session: Session, document_id: int) -> ShipmentDocument:
    document = session.get(ShipmentDocument, document_id)
    if document is None:
        raise NotFound(f"Document {document_id} not found")
    return document
