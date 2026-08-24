"""Ops account authentication and password management. `change_ops_password`
is the only place `OpsUser.token_version` is bumped -- see
`utils.security.get_current_ops_user` for how that revokes every
previously-issued session, not just the one making the change.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from utils.errors import InvalidPasswordChange, NotFound, Unauthorized
from models.ops_user import OpsUser
from utils.security import hash_password, verify_password


def authenticate_ops_user(session: Session, username: str, password: str) -> OpsUser:
    ops_user = session.execute(select(OpsUser).where(OpsUser.username == username)).scalar_one_or_none()
    if ops_user is None or not ops_user.is_active or not verify_password(password, ops_user.password_hash):
        # Same message for "no such user", "wrong password", and
        # "deactivated" -- doesn't tell a caller which one it was.
        raise Unauthorized("Invalid username or password.")
    return ops_user


def create_ops_user(session: Session, *, name: str, username: str, password: str) -> OpsUser:
    ops_user = OpsUser(name=name, username=username, password_hash=hash_password(password))
    session.add(ops_user)
    session.flush()
    return ops_user


def change_ops_password(
    session: Session,
    ops_user: OpsUser,
    *,
    current_password: str,
    new_password: str,
    confirm_new_password: str,
) -> OpsUser:
    if not verify_password(current_password, ops_user.password_hash):
        raise Unauthorized("Current password is incorrect.")
    if new_password != confirm_new_password:
        raise InvalidPasswordChange("New password and confirmation do not match.")
    if len(new_password) < 8:
        raise InvalidPasswordChange("New password must be at least 8 characters.")

    ops_user.password_hash = hash_password(new_password)
    ops_user.token_version += 1
    session.flush()
    return ops_user


def get_ops_user(session: Session, ops_user_id: int) -> OpsUser:
    ops_user = session.get(OpsUser, ops_user_id)
    if ops_user is None:
        raise NotFound(f"Ops user {ops_user_id} not found")
    return ops_user
