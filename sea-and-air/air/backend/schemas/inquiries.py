from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from models.enums import TransportMode


class InquiryCreate(BaseModel):
    customer_id: int
    origin: str = Field(min_length=1, max_length=120)
    destination: str = Field(min_length=1, max_length=120)
    mode: TransportMode
    cargo_type: str = Field(min_length=1, max_length=120)
    weight_kg: Decimal = Field(gt=0)
    volume_cbm: Decimal = Field(gt=0)
    dimensions: str | None = Field(default=None, max_length=200)
    ready_date: date | None = None
    incoterm: str = Field(min_length=1, max_length=10)
    description: str | None = None


class InquiryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    origin: str
    destination: str
    mode: TransportMode
    cargo_type: str
    weight_kg: Decimal
    volume_cbm: Decimal
    dimensions: str | None
    ready_date: date | None
    incoterm: str
    description: str | None
    created_at: datetime
    updated_at: datetime
