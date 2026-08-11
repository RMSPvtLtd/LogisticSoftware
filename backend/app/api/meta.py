from fastapi import APIRouter

from app.models.enums import OPERATIONAL_STAGE_ORDER, TransportMode, stage_group, stage_label
from app.schemas.meta import StageMeta, StagesMetaResponse

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/stages", response_model=StagesMetaResponse)
def get_stages(mode: TransportMode = TransportMode.AIR) -> StagesMetaResponse:
    # Every mode walks the identical OPERATIONAL_STAGE_ORDER -- only the
    # label/group text can differ per mode (see enums.STAGE_LABEL_OVERRIDES_BY_MODE).
    # Defaulting to AIR keeps existing callers (no ?mode= param) unchanged.
    return StagesMetaResponse(
        stages=[
            StageMeta(stage=stage, label=stage_label(stage, mode), group=stage_group(stage, mode))
            for stage in OPERATIONAL_STAGE_ORDER
        ]
    )
