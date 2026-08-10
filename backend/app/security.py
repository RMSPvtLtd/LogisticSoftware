"""Worker authentication: password hashing, JWT issuance/verification, and
the `get_current_worker` dependency that turns a bearer token into a
`Worker` row. This is the only part of the application with real login —
the ops/admin side still uses the unauthenticated `current_actor` header
(see `app.dependencies`), which is unchanged.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import Unauthorized
from app.models.worker import Worker

JWT_ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(worker_id: int) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {"sub": str(worker_id), "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def _decode_worker_id(token: str) -> int:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise Unauthorized("Invalid or expired session; please log in again.") from exc
    try:
        return int(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise Unauthorized("Invalid session token.") from exc


def get_current_worker(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> Worker:
    """Resolves the bearer token in the Authorization header into an active
    Worker, or raises Unauthorized. Every worker-portal route depends on
    this — a shipment queue/completion action can never proceed without a
    verified, active worker identity.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("Missing bearer token.")
    token = authorization[len("bearer "):].strip()
    worker_id = _decode_worker_id(token)

    worker = db.execute(select(Worker).where(Worker.id == worker_id)).scalar_one_or_none()
    if worker is None or not worker.is_active:
        raise Unauthorized("Account not found or deactivated.")
    return worker
