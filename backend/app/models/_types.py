"""Owns how Python enums are persisted. Every model column backed by one of the
enums in `app.models.enums` goes through `portable_enum` so the storage
decision — VARCHAR + CHECK, not a native database enum type — is made once and
never repeated at each call site. This is what keeps SQLite (tests) and
PostgreSQL (production) schema-compatible.
"""

from typing import TypeVar

from sqlalchemy import Enum as SAEnum

E = TypeVar("E")


def portable_enum(enum_cls: type[E], length: int = 30) -> SAEnum:
    return SAEnum(enum_cls, native_enum=False, length=length, validate_strings=True)
