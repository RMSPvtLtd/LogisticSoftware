"""The worker-facing surface: a queue of shipments waiting at the worker's
area stage, and the one action a worker can take on them. Every route here
requires `get_current_worker` — there is no path to these endpoints without
a valid, active worker token.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotFound
from app.models.shipment import Shipment
from app.models.worker import Worker
from app.schemas.worker_portal import CompleteStageRequest, WorkerQueueItem, from_shipment
from app.security import get_current_worker
from app.services.workers import complete_worker_stage, worker_queue

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
