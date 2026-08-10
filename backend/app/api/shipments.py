from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import current_actor
from app.errors import NotFound
from app.models.enums import ShipmentStage, TransportMode
from app.models.inquiry import Inquiry
from app.models.shipment import Shipment, ShipmentReference
from app.schemas.shipments import ReferenceCreateRequest, RiskUpdateRequest, ShipmentRead, StatusCorrectionRequest
from app.services.transitions import correct_stage, set_risk

router = APIRouter(prefix="/shipments", tags=["shipments"])

# There is deliberately no ops-facing "advance to next stage" endpoint here.
# Normal progression belongs to workers, scoped to their area (see
# app.api.worker_portal) -- ops only fixes mistakes, via correct_status
# below, and manages risk/references, which are independent of stage.


def _get_shipment(db: Session, shipment_id: int) -> Shipment:
    shipment = db.get(Shipment, shipment_id)
    if shipment is None:
        raise NotFound(f"Shipment {shipment_id} not found")
    return shipment


@router.get("", response_model=list[ShipmentRead])
def list_shipments(
    stage: ShipmentStage | None = None,
    at_risk: bool | None = None,
    mode: TransportMode | None = None,
    db: Session = Depends(get_db),
) -> list[Shipment]:
    stmt = select(Shipment)
    if stage is not None:
        stmt = stmt.where(Shipment.stage == stage)
    if at_risk is not None:
        stmt = stmt.where(Shipment.is_at_risk == at_risk)
    if mode is not None:
        stmt = stmt.join(Inquiry, Inquiry.id == Shipment.inquiry_id).where(Inquiry.mode == mode)
    return list(db.execute(stmt.order_by(Shipment.id)).scalars())


@router.get("/{shipment_id}", response_model=ShipmentRead)
def get_shipment(shipment_id: int, db: Session = Depends(get_db)) -> Shipment:
    return _get_shipment(db, shipment_id)


@router.post("/{shipment_id}/status/correct", response_model=ShipmentRead)
def correct_status(
    shipment_id: int,
    payload: StatusCorrectionRequest,
    actor: str = Depends(current_actor),
    db: Session = Depends(get_db),
) -> Shipment:
    shipment = _get_shipment(db, shipment_id)
    correct_stage(db, shipment, payload.stage, actor=actor, reason=payload.reason)
    return shipment


@router.post("/{shipment_id}/references", response_model=ShipmentRead, status_code=201)
def add_reference(
    shipment_id: int, payload: ReferenceCreateRequest, db: Session = Depends(get_db)
) -> Shipment:
    shipment = _get_shipment(db, shipment_id)
    shipment.references.append(ShipmentReference(type=payload.type, value=payload.value))
    db.flush()
    return shipment


@router.post("/{shipment_id}/risk", response_model=ShipmentRead)
def update_risk(
    shipment_id: int,
    payload: RiskUpdateRequest,
    actor: str = Depends(current_actor),
    db: Session = Depends(get_db),
) -> Shipment:
    shipment = _get_shipment(db, shipment_id)
    set_risk(db, shipment, is_at_risk=payload.is_at_risk, risk_reason=payload.risk_reason, actor=actor)
    return shipment
