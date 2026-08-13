"""The worker-facing surface: a queue of shipments waiting at the worker's
area stage, the action a worker can take to advance one, and optional PDF
attachments a worker can add to a shipment while it's in their queue. Every
route here requires `get_current_worker` — there is no path to these
endpoints without a valid, active worker token.
"""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from db import get_db
from utils.errors import NotFound
from models.document import ShipmentDocument
from models.shipment import Shipment
from models.worker import Worker
from schemas.documents import ShipmentDocumentRead
from schemas.worker_portal import CompleteStageRequest, WorkerQueueItem, from_shipment
from utils.security import get_current_worker
from services.workers import complete_worker_stage, list_worker_documents, upload_worker_document, worker_queue

router = APIRouter(prefix="/worker", tags=["worker-portal"])


@router.get("/queue", response_model=list[WorkerQueueItem])
def get_queue(
    worker: Worker = Depends(get_current_worker), db: Session = Depends(get_db)
) -> list[WorkerQueueItem]:
    return [from_shipment(s) for s in worker_queue(db, worker)]


@router.post("/shipments/{shipment_id}/complete", response_model=WorkerQueueItem)
def complete_stage(
    shipment_id: int,
    payload: CompleteStageRequest,
    worker: Worker = Depends(get_current_worker),
    db: Session = Depends(get_db),
) -> WorkerQueueItem:
    shipment = db.get(Shipment, shipment_id)
    if shipment is None:
        raise NotFound(f"Shipment {shipment_id} not found")
    complete_worker_stage(db, worker, shipment, note=payload.note)
    return from_shipment(shipment)


def _get_shipment(db: Session, shipment_id: int) -> Shipment:
    shipment = db.get(Shipment, shipment_id)
    if shipment is None:
        raise NotFound(f"Shipment {shipment_id} not found")
    return shipment


@router.post("/shipments/{shipment_id}/documents", response_model=ShipmentDocumentRead, status_code=201)
async def upload_document(
    shipment_id: int,
    file: UploadFile = File(...),
    worker: Worker = Depends(get_current_worker),
    db: Session = Depends(get_db),
) -> ShipmentDocument:
    shipment = _get_shipment(db, shipment_id)
    data = await file.read()
    return upload_worker_document(
        db, worker, shipment, filename=file.filename, content_type=file.content_type, data=data
    )


@router.get("/shipments/{shipment_id}/documents", response_model=list[ShipmentDocumentRead])
def list_documents(
    shipment_id: int, worker: Worker = Depends(get_current_worker), db: Session = Depends(get_db)
) -> list[ShipmentDocument]:
    shipment = _get_shipment(db, shipment_id)
    return list_worker_documents(db, worker, shipment)
