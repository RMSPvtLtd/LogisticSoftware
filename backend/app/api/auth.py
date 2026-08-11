from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.worker import Worker
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.workers import WorkerRead
from app.security import create_access_token, get_current_worker
from app.services.workers import authenticate_worker

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    worker = authenticate_worker(db, payload.username, payload.password)
    token = create_access_token(worker.id, "worker")
    return LoginResponse(access_token=token, worker=worker)


@router.get("/me", response_model=WorkerRead)
def me(worker: Worker = Depends(get_current_worker)) -> Worker:
    return worker
