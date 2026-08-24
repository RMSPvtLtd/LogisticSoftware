from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from db import get_db
from models.worker import Worker
from schemas.auth import LoginRequest, LoginResponse
from schemas.workers import WorkerRead
from utils import rate_limit, security_log
from utils.errors import TooManyAttempts, Unauthorized
from utils.security import create_access_token, get_current_worker
from services.workers import authenticate_worker

router = APIRouter(prefix="/auth", tags=["auth"])

SURFACE = "worker"


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    ip = rate_limit.client_ip(request)
    try:
        rate_limit.check_not_locked_out(SURFACE, payload.username, request)
    except TooManyAttempts:
        security_log.auth_lockout(surface=SURFACE, username=payload.username, ip=ip)
        raise

    try:
        worker = authenticate_worker(db, payload.username, payload.password)
    except Unauthorized:
        rate_limit.record_failure(SURFACE, payload.username, request)
        security_log.auth_failure(
            surface=SURFACE, username=payload.username, ip=ip, reason="invalid_credentials"
        )
        raise

    rate_limit.record_success(SURFACE, payload.username, request)
    security_log.auth_success(surface=SURFACE, username=worker.username, ip=ip)
    token = create_access_token(worker.id, "worker")
    return LoginResponse(access_token=token, worker=worker)


@router.get("/me", response_model=WorkerRead)
def me(worker: Worker = Depends(get_current_worker)) -> Worker:
    return worker
