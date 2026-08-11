from pydantic import BaseModel

from app.models.enums import ShipmentStage


class StageMeta(BaseModel):
    stage: ShipmentStage
    label: str
    # Display section this stage belongs to (e.g. "Airport"), or None for a
    # standalone stage. Purely presentational -- see app.models.enums.STAGE_GROUPS.
    group: str | None


class StagesMetaResponse(BaseModel):
    stages: list[StageMeta]
