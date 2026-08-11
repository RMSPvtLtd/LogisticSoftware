from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models.enums import ShipmentStage


class AreaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    stage: ShipmentStage


class WorkerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    username: str
    is_active: bool
    area: AreaRead
    created_at: datetime


class WorkerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    username: str = Field(min_length=3, max_length=60, pattern=r"^[a-zA-Z0-9._-]+$")
    password: str = Field(min_length=6, max_length=200)
    area_id: int


class WorkerUpdate(BaseModel):
    is_active: bool | None = None
    area_id: int | None = None
