"""Bearer-token authentication for all three principal types: worker,
customer, and ops. All three share the same JWT primitives, but every token
carries a `typ` claim ("worker"/"customer"/"ops") that is checked on decode --
a worker's token can never be replayed against a customer-portal or ops
route and vice versa, even though all three are just integer primary keys
under the hood.

Ops tokens additionally carry a `tv` (token_version) claim. It has no
equivalent for worker/customer because only ops has a self-service
"change password" action (`services.ops_users.change_ops_password`); when
that runs, it bumps `OpsUser.token_version`, and `get_current_ops_user`
rejects any token whose `tv` claim doesn't match the current value. This is
the practical, stateless way to revoke every previously issued ops session
on a password change without a token blocklist table.
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
from models.ops_user import OpsUser
from models.worker import Worker

JWT_ALGORITHM = "HS256"

SubjectType = Literal["worker", "customer", "ops"]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(subject_id: int, subject_type: SubjectType, *, token_version: int | None = None) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {"sub": str(subject_id), "typ": subject_type, "exp": expires_at}
    if token_version is not None:
        payload["tv"] = token_version
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def _decode_payload(token: str, expected_type: SubjectType) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise Unauthorized("Invalid or expired session; please log in again.") from exc
    if payload.get("typ") != expected_type:
        raise Unauthorized("Invalid session token.")
    return payload


def _decode_subject_id(token: str, expected_type: SubjectType) -> int:
    payload = _decode_payload(token, expected_type)
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


def get_current_ops_user(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> OpsUser:
    """Resolves the bearer token into an active OpsUser, additionally
    rejecting it if its `tv` claim doesn't match the account's current
    `token_version` -- the mechanism that makes a password change revoke
    every session issued before it, not just the one that changed it.
    """
    payload = _decode_payload(_bearer_token(authorization), "ops")
    try:
        ops_user_id = int(payload["sub"])
        token_version = int(payload["tv"])
    except (KeyError, ValueError) as exc:
        raise Unauthorized("Invalid session token.") from exc

    ops_user = db.execute(select(OpsUser).where(OpsUser.id == ops_user_id)).scalar_one_or_none()
    if ops_user is None or not ops_user.is_active:
        raise Unauthorized("Account not found or deactivated.")
    if ops_user.token_version != token_version:
        raise Unauthorized("Session no longer valid; please log in again.")
    return ops_user
