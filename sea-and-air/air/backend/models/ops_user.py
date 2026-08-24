from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db import Base
from models._mixins import TimestampMixin


class OpsUser(TimestampMixin, Base):
    """An internal ops/admin account. Mirrors `models.worker.Worker` minus
    area scoping -- ops isn't restricted to one stage. `token_version` is
    bumped by `services.ops_users.change_ops_password` so every token issued
    before a password change is rejected by `utils.security.get_current_ops_user`
    immediately, without needing a token blocklist table.
    """

    __tablename__ = "ops_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
