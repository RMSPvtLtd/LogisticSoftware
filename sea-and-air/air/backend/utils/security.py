"""Bearer-token authentication for the two portal surfaces (worker and
customer). Both share the same JWT primitives, but every token carries a
`typ` claim ("worker" or "customer") that is checked on decode -- a worker's
token can never be replayed against a customer-portal route and vice versa,
even though both are just integer primary keys under the hood. The ops/admin
side still uses the unauthenticated `current_actor` header (see
`utils.dependencies`), which is unchanged.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_settings
from db import get_db
from utils.errors import Unauthorized
from models.customer import Customer
from models.worker import Worker

JWT_ALGORITHM = "HS256"

SubjectType = Literal["worker", "customer"]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(subject_id: int, subject_type: SubjectType) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {"sub": str(subject_id), "typ": subject_type, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def _decode_subject_id(token: str, expected_type: SubjectType) -> int:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise Unauthorized("Invalid or expired session; please log in again.") from exc
    if payload.get("typ") != expected_type:
        raise Unauthorized("Invalid session token.")
    try:
        return int(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise Unauthorized("Invalid session token.") from exc


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("Missing bearer token.")
    return authorization[len("bearer "):].strip()


def get_current_worker(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> Worker:
    """Resolves the bearer token in the Authorization header into an active
    Worker, or raises Unauthorized. Every worker-portal route depends on
    this — a shipment queue/completion action can never proceed without a
    verified, active worker identity.
    """
    worker_id = _decode_subject_id(_bearer_token(authorization), "worker")

    worker = db.execute(select(Worker).where(Worker.id == worker_id)).scalar_one_or_none()
    if worker is None or not worker.is_active:
        raise Unauthorized("Account not found or deactivated.")
    return worker


def get_current_customer(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> Customer:
    """Resolves the bearer token into an active, portal-enabled Customer.
    Every customer-portal route depends on this — a customer can never see
    another customer's shipments or quotes, since every query in
    `api.customer_portal` is scoped to `customer.id` from here, not from
    anything the client sends.
    """
    customer_id = _decode_subject_id(_bearer_token(authorization), "customer")

    customer = db.execute(select(Customer).where(Customer.id == customer_id)).scalar_one_or_none()
    if customer is None or not customer.portal_active or customer.username is None:
        raise Unauthorized("Account not found or deactivated.")
    return customer
