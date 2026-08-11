from fastapi import APIRouter

from app.models.enums import OPERATIONAL_STAGE_ORDER, stage_group, stage_label
from app.schemas.meta import StageMeta, StagesMetaResponse

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/stages", response_model=StagesMetaResponse)
def get_stages() -> StagesMetaResponse:
    return StagesMetaResponse(
        stages=[
            StageMeta(stage=stage, label=stage_label(stage), group=stage_group(stage))
            for stage in OPERATIONAL_STAGE_ORDER
        ]
    )
