from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from db import get_db
from models.ops_user import OpsUser
from schemas.auth import LoginRequest
from schemas.ops_users import ChangePasswordRequest, OpsLoginResponse, OpsUserRead
from utils import rate_limit, security_log
from utils.errors import TooManyAttempts, Unauthorized
from utils.security import create_access_token, get_current_ops_user
from services.ops_users import authenticate_ops_user, change_ops_password

router = APIRouter(prefix="/ops", tags=["ops-auth"])

SURFACE = "ops"


@router.post("/login", response_model=OpsLoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> OpsLoginResponse:
    ip = rate_limit.client_ip(request)
    try:
        rate_limit.check_not_locked_out(SURFACE, payload.username, request)
    except TooManyAttempts:
        security_log.auth_lockout(surface=SURFACE, username=payload.username, ip=ip)
        raise

    try:
        ops_user = authenticate_ops_user(db, payload.username, payload.password)
    except Unauthorized:
        rate_limit.record_failure(SURFACE, payload.username, request)
        security_log.auth_failure(
            surface=SURFACE, username=payload.username, ip=ip, reason="invalid_credentials"
        )
        raise

    rate_limit.record_success(SURFACE, payload.username, request)
    security_log.auth_success(surface=SURFACE, username=ops_user.username, ip=ip)
    token = create_access_token(ops_user.id, "ops", token_version=ops_user.token_version)
    return OpsLoginResponse(access_token=token, ops_user=ops_user)


@router.get("/me", response_model=OpsUserRead)
def me(ops_user: OpsUser = Depends(get_current_ops_user)) -> OpsUser:
    return ops_user


@router.post("/change-password", response_model=OpsUserRead)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    ops_user: OpsUser = Depends(get_current_ops_user),
    db: Session = Depends(get_db),
) -> OpsUser:
    updated = change_ops_password(
        db,
        ops_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        confirm_new_password=payload.confirm_new_password,
    )
    security_log.password_changed(
        surface=SURFACE, username=updated.username, ip=rate_limit.client_ip(request)
    )
    return updated
