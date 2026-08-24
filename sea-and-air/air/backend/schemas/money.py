"""The single definition of what a valid money value is on the wire.

Every monetary request field uses `MoneyAmount` so the bounds are stated
once rather than re-derived (or forgotten) per schema. The constraints
mirror the database columns they land in -- `NUMERIC(12, 2)` -- so a value
that passes validation can always be stored: without this, an out-of-range
amount reaches the driver and fails at flush time as a 500 whose message
embeds the SQL statement.

Rejected by construction: negatives, NaN, Infinity (Pydantic's `ge`/`le`
comparison refuses non-finite Decimals), more than 2 decimal places, and
anything at or beyond 10^10.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import Field

# NUMERIC(12, 2) holds at most 10 integer digits plus 2 decimal places.
MAX_MONEY = Decimal("9999999999.99")

MoneyAmount = Annotated[
    Decimal,
    Field(ge=Decimal("0"), le=MAX_MONEY, max_digits=12, decimal_places=2),
]
