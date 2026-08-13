from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.orm import Session

from db import get_db
from utils.dependencies import current_actor
from utils.errors import NotFound
from models.shipment import Shipment
from schemas.documents import ShipmentDocumentRead
from services.documents import get_document, list_documents
from services.documents import upload_document as upload_document_service

router = APIRouter(prefix="/shipments", tags=["documents"])

# Flat, not nested under /shipments -- downloading a document by id doesn't
# need the shipment_id in the path.
doc_router = APIRouter(prefix="/documents", tags=["documents"])


def _get_shipment(db: Session, shipment_id: int) -> Shipment:
    shipment = db.get(Shipment, shipment_id)
    if shipment is None:
        raise NotFound(f"Shipment {shipment_id} not found")
    return shipment


@router.post("/{shipment_id}/documents", response_model=ShipmentDocumentRead, status_code=201)
async def upload_document(
    shipment_id: int,
    file: UploadFile = File(...),
    actor: str = Depends(current_actor),
    db: Session = Depends(get_db),
):
    shipment = _get_shipment(db, shipment_id)
    data = await file.read()
    return upload_document_service(
        db, shipment, filename=file.filename, content_type=file.content_type, data=data, actor=actor
    )


@router.get("/{shipment_id}/documents", response_model=list[ShipmentDocumentRead])
def list_shipment_documents(shipment_id: int, db: Session = Depends(get_db)):
    _get_shipment(db, shipment_id)
    return list_documents(db, shipment_id)


@doc_router.get("/{document_id}")
def download_document(document_id: int, db: Session = Depends(get_db)) -> Response:
    document = get_document(db, document_id)
    return Response(
        content=document.data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{document.filename}"'},
    )
