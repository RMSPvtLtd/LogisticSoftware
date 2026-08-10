"""Ops-facing shipment schemas. These are internal — they include actor,
source, and is_internal on status events, none of which the customer
tracking endpoint may expose. `schemas/tracking.py` is a deliberately
separate, independent set of models for that reason; nothing here is reused
there.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import EventSource, ReferenceType, ShipmentStage


class ShipmentReferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: ReferenceType
    value: str
    created_at: datetime


class StatusEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stage: ShipmentStage
    timestamp: datetime
    actor: str
    note: str | None
    source: EventSource
    is_stage_change: bool
    is_internal: bool


class ShipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    inquiry_id: int
    quote_id: int
    job_number: str
    stage: ShipmentStage
    is_at_risk: bool
    risk_reason: str | None
    created_at: datetime
    updated_at: datetime
    references: list[ShipmentReferenceRead]
    status_events: list[StatusEventRead]


# Request schemas. `source` is never accepted here — it is assigned by the
# server based on which operation is being performed (see
# app.models.enums.EventSource and app.services.transitions).


class StatusUpdateRequest(BaseModel):
    stage: ShipmentStage
    note: str | None = None


class StatusCorrectionRequest(BaseModel):
    stage: ShipmentStage
    reason: str = Field(min_length=1)


class ReferenceCreateRequest(BaseModel):
    type: ReferenceType
    value: str = Field(min_length=1, max_length=120)


class RiskUpdateRequest(BaseModel):
    is_at_risk: bool
    risk_reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _reason_required_when_at_risk(self) -> "RiskUpdateRequest":
        if self.is_at_risk and not (self.risk_reason and self.risk_reason.strip()):
            raise ValueError("risk_reason is required when is_at_risk is true")
        return self
