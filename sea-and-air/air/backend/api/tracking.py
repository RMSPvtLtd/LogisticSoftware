from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from schemas.tracking import TrackingResult, from_shipment
from services.tracking import find_shipment_for_tracking

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/{reference}", response_model=TrackingResult)
def track(reference: str, db: Session = Depends(get_db)) -> TrackingResult:
    shipment = find_shipment_for_tracking(db, reference)
    return from_shipment(shipment)
