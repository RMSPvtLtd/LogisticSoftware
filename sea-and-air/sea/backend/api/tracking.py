"""The one tracking endpoint the sea vertical exposes. Extending this
router (not creating a second one) is how a future provider or a
richer request shape gets added -- there is exactly one /api/tracking
route, matching Phase 6's "extend, don't duplicate" rule.
"""

from fastapi import APIRouter

from config import get_settings
from schemas.tracking import ContainerTrackingRequest, TrackingResult
from services.tracking_service import track_container
from utils.cache import TTLCache
from utils.validation import normalize_container_number

router = APIRouter(prefix="/api", tags=["tracking"])

# Module-level so the cache survives across requests within one process --
# a dependency-injected *instance* would be recreated (and therefore
# emptied) on every request, defeating the point.
_cache: TTLCache[TrackingResult] = TTLCache(ttl_seconds=get_settings().tracking_cache_ttl_seconds)


@router.post("/tracking", response_model=TrackingResult)
def track(payload: ContainerTrackingRequest) -> TrackingResult:
    container_number = normalize_container_number(payload.container_number)

    cached = _cache.get(container_number)
    if cached is not None:
        return cached

    result = track_container(container_number)
    _cache.set(container_number, result)
    return result
