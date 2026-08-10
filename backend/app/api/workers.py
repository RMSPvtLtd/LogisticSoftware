"""Admin/ops management of Areas and Workers. Unauthenticated like the rest
of the ops API (see app.dependencies.current_actor) — the ops side has no
login in this MVP. Only the worker portal (app.api.worker_portal) requires
a bearer token.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotFound
from app.models.worker import Area, Worker
from app.schemas.workers import AreaRead, WorkerCreate, WorkerRead, WorkerUpdate
from app.services.workers import create_worker

router = APIRouter(tags=["workers"])


@router.get("/areas", response_model=list[AreaRead])
def list_areas(db: Session = Depends(get_db)) -> list[Area]:
    return list(db.execute(select(Area).order_by(Area.id)).scalars())


@router.get("/workers", response_model=list[WorkerRead])
def list_workers(db: Session = Depends(get_db)) -> list[Worker]:
    return list(db.execute(select(Worker).order_by(Worker.id)).scalars())


@router.post("/workers", response_model=WorkerRead, status_code=201)
def create_worker_route(payload: WorkerCreate, db: Session = Depends(get_db)) -> Worker:
    return create_worker(
        db, name=payload.name, username=payload.username, password=payload.password, area_id=payload.area_id
    )


@router.patch("/workers/{worker_id}", response_model=WorkerRead)
def update_worker(worker_id: int, payload: WorkerUpdate, db: Session = Depends(get_db)) -> Worker:
    worker = db.get(Worker, worker_id)
    if worker is None:
        raise NotFound(f"Worker {worker_id} not found")
    if payload.is_active is not None:
        worker.is_active = payload.is_active
    if payload.area_id is not None:
        if db.get(Area, payload.area_id) is None:
            raise NotFound(f"Area {payload.area_id} not found")
        worker.area_id = payload.area_id
    db.flush()
    return worker
