"""Owns validation and storage of PDF attachments on a Shipment. PDFs are
stored inline in Postgres (see `models.document.ShipmentDocument`) -- a
deliberate choice for this deployment (Vercel serverless has no persistent
disk), not a stopgap. Validation lives here rather than in a Pydantic schema
because `UploadFile`/`File()` multipart params aren't schema fields, and
this keeps the check usable outside a request (tests) same as every other
service in this package.

SECURITY: the uploaded filename is fully attacker-controlled and is never
trusted. Storing bytes in the database means it never reaches a filesystem
path, so path traversal is structurally impossible here -- but the name is
still echoed back in a `Content-Disposition` header on download, so
`sanitize_filename` strips anything that could break out of that header or
be reinterpreted as a path if storage ever changes. Content type is decided
by inspecting the actual bytes, never the client-declared MIME type or the
extension.
"""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from utils.errors import InvalidDocument, NotFound
from models.document import ShipmentDocument
from models.enums import DocumentType
from models.shipment import Shipment

# Vercel Functions enforce a hard 4.5 MB request-body cap platform-wide
# (regardless of plan) -- requests over that never reach handler code at
# all. 4 MB leaves headroom for multipart boundary/header overhead.
MAX_DOCUMENT_SIZE_BYTES = 4 * 1024 * 1024
ALLOWED_CONTENT_TYPE = "application/pdf"
PDF_MAGIC = b"%PDF-"

MAX_FILENAME_LENGTH = 120
# Everything outside this set is replaced. Excludes path separators, quotes,
# control characters, and semicolons -- i.e. every character that could
# traverse a path or terminate/extend a Content-Disposition parameter.
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._ -]")


def sanitize_filename(raw: str | None) -> str:
    """Reduces an attacker-controlled filename to a safe, display-only name.

    Keeps it recognisable to the user who uploaded it (ops needs to tell
    `awb-scan.pdf` from `gd-form.pdf`) while guaranteeing it contains no
    path separators, quotes, or control characters. Always returns a
    non-empty name ending in `.pdf`.
    """
    # Take the basename first, so "../../etc/passwd" can't survive as a path
    # even in part -- then strip anything still outside the allowlist.
    candidate = (raw or "").replace("\\", "/").rsplit("/", 1)[-1]
    candidate = _UNSAFE_FILENAME_CHARS.sub("_", candidate).strip(" .")

    if not candidate:
        return "document.pdf"
    if not candidate.lower().endswith(".pdf"):
        candidate = f"{candidate}.pdf"
    if len(candidate) > MAX_FILENAME_LENGTH:
        candidate = candidate[: MAX_FILENAME_LENGTH - 4].rstrip(" .") + ".pdf"
    return candidate


def upload_document(
    session: Session,
    shipment: Shipment,
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
    actor: str,
    document_type: DocumentType | None = None,
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
        document_type=document_type or DocumentType.OTHER,
        filename=sanitize_filename(filename),
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
