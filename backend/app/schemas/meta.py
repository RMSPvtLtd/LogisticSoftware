from pydantic import BaseModel

from app.models.enums import ShipmentStage


class StageMeta(BaseModel):
    stage: ShipmentStage
    label: str


class StagesMetaResponse(BaseModel):
    stages: list[StageMeta]
