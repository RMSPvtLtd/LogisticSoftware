"""Wire shapes for the airline weekly-schedule reference list. Reference-only
data (see models.airline_schedule.AirlineSchedule) -- no cross-field pricing
validation needed here, just shape checks."""

import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.enums import TransportMode

DayOfWeek = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class AirlineScheduleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    airline_name: str = Field(min_length=1, max_length=120)
    origin: str = Field(min_length=1, max_length=120)
    destination: str = Field(min_length=1, max_length=120)
    mode: TransportMode
    days_of_week: list[DayOfWeek] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=2000)


class AirlineScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    airline_name: str
    origin: str
    destination: str
    mode: TransportMode
    days_of_week: list[DayOfWeek]
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("days_of_week", mode="before")
    @classmethod
    def _decode_days(cls, value: object) -> object:
        # Stored as a JSON-encoded string (models.airline_schedule.AirlineSchedule
        # .days_of_week) -- decode it back into a list for the API response.
        return json.loads(value) if isinstance(value, str) else value
