from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models.rate_card import RateCard
from schemas.rate_cards import RateCardCreate, RateCardRead
from services.rate_cards import create_rate_card, delete_rate_card, get_rate_card, update_rate_card
from utils.security import get_current_ops_user

router = APIRouter(prefix="/rate-cards", tags=["rate-cards"], dependencies=[Depends(get_current_ops_user)])


@router.post("", response_model=RateCardRead, status_code=201)
def create_rate_card_route(payload: RateCardCreate, db: Session = Depends(get_db)) -> RateCard:
    return create_rate_card(db, payload)


@router.get("", response_model=list[RateCardRead])
def list_rate_cards(db: Session = Depends(get_db)) -> list[RateCard]:
    return list(db.execute(select(RateCard).order_by(RateCard.origin, RateCard.destination, RateCard.id)).scalars())


@router.get("/{rate_card_id}", response_model=RateCardRead)
def get_rate_card_route(rate_card_id: int, db: Session = Depends(get_db)) -> RateCard:
    return get_rate_card(db, rate_card_id)


@router.patch("/{rate_card_id}", response_model=RateCardRead)
def update_rate_card_route(rate_card_id: int, payload: RateCardCreate, db: Session = Depends(get_db)) -> RateCard:
    return update_rate_card(db, rate_card_id, payload)


@router.delete("/{rate_card_id}", status_code=204)
def delete_rate_card_route(rate_card_id: int, db: Session = Depends(get_db)) -> None:
    delete_rate_card(db, rate_card_id)
