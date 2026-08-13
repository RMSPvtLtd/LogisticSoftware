from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from models.enums import ChargeKind, QuoteStatus, ShipmentStage


class QuoteGenerateRequest(BaseModel):
    inquiry_id: int


class QuoteLineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: ChargeKind
    description: str
    quantity: Decimal
    unit_price: Decimal
    calculated_total: Decimal
    final_total: Decimal
    markup_amount: Decimal
    is_manual_override: bool


class QuoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    inquiry_id: int
    status: QuoteStatus
    shipment_stage: ShipmentStage | None
    currency: str
    subtotal: Decimal
    markup_amount: Decimal
    total: Decimal
    valid_until: date
    created_at: datetime
    updated_at: datetime
    line_items: list[QuoteLineItemRead]


class LineItemOverrideRequest(BaseModel):
    line_item_id: int
    final_total: Decimal = Field(ge=0)


class QuoteLineItemsOverrideRequest(BaseModel):
    overrides: list[LineItemOverrideRequest] = Field(min_length=1)
