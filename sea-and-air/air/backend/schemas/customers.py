import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CustomerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    email: str = Field(max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = None

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        if not _EMAIL_PATTERN.match(value):
            raise ValueError("email must be a valid email address")
        return value


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company_name: str | None
    email: str
    phone: str | None
    address: str | None
    username: str | None
    portal_active: bool
    created_at: datetime
    updated_at: datetime


class CustomerPortalCredentials(BaseModel):
    """Ops-only: (re)issues a customer's portal login. Sets a new username
    and password and enables access in one step -- there's no separate
    "create username" and "set password" action."""
    model_config = ConfigDict(extra="forbid")


    username: str = Field(min_length=3, max_length=60, pattern=r"^[a-zA-Z0-9._-]+$")
    password: str = Field(min_length=6, max_length=200)


class CustomerPortalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool
