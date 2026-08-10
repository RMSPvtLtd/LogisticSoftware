import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)
    email: str = Field(max_length=320)
    phone: str | None = Field(default=None, max_length=50)

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
    created_at: datetime
    updated_at: datetime
