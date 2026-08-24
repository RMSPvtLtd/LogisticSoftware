"""Rate card CRUD. Breaks and charges are owned entirely by their rate card
(`cascade="all, delete-orphan"` on the relationship) -- there is no route
that edits a single break or charge in isolation, so update always replaces
the full set rather than diffing it. This keeps the semantics simple: what
you PATCH is what you get back, with no partial-merge surprises."""

from sqlalchemy.orm import Session

from models.rate_card import RateCard, RateCardBreak, RateCardCharge
from schemas.rate_cards import RateCardCreate
from utils.errors import NotFound


def _apply(rate_card: RateCard, payload: RateCardCreate) -> None:
    rate_card.origin = payload.origin
    rate_card.destination = payload.destination
    rate_card.mode = payload.mode
    rate_card.carrier = payload.carrier
    rate_card.currency = payload.currency
    rate_card.valid_from = payload.valid_from
    rate_card.valid_until = payload.valid_until
    rate_card.minimum_charge = payload.minimum_charge
    rate_card.breaks = [
        RateCardBreak(
            min_weight=b.min_weight,
            max_weight=b.max_weight,
            min_volume=b.min_volume,
            max_volume=b.max_volume,
            unit=b.unit,
            rate=b.rate,
            description=b.description,
        )
        for b in payload.breaks
    ]
    rate_card.charges = [
        RateCardCharge(kind=c.kind, description=c.description, basis=c.basis, amount=c.amount)
        for c in payload.charges
    ]


def create_rate_card(session: Session, payload: RateCardCreate) -> RateCard:
    rate_card = RateCard()
    _apply(rate_card, payload)
    session.add(rate_card)
    session.flush()
    return rate_card


def get_rate_card(session: Session, rate_card_id: int) -> RateCard:
    rate_card = session.get(RateCard, rate_card_id)
    if rate_card is None:
        raise NotFound(f"Rate card {rate_card_id} not found")
    return rate_card


def update_rate_card(session: Session, rate_card_id: int, payload: RateCardCreate) -> RateCard:
    rate_card = get_rate_card(session, rate_card_id)
    _apply(rate_card, payload)
    session.flush()
    return rate_card


def delete_rate_card(session: Session, rate_card_id: int) -> None:
    rate_card = get_rate_card(session, rate_card_id)
    session.delete(rate_card)
    session.flush()
