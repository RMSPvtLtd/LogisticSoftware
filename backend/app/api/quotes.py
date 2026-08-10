from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import current_actor
from app.errors import NotFound
from app.models.quote import Quote
from app.schemas.quotes import QuoteGenerateRequest, QuoteLineItemsOverrideRequest, QuoteRead
from app.schemas.shipments import ShipmentRead
from app.services.quotes import LineItemOverride, accept_quote, generate_quote, override_line_items, send_quote

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.post("/generate", response_model=QuoteRead, status_code=201)
def generate(payload: QuoteGenerateRequest, db: Session = Depends(get_db)) -> Quote:
    return generate_quote(db, payload.inquiry_id)


@router.get("", response_model=list[QuoteRead])
def list_quotes(db: Session = Depends(get_db)) -> list[Quote]:
    return list(db.execute(select(Quote).order_by(Quote.id)).scalars())


@router.get("/{quote_id}", response_model=QuoteRead)
def get_quote(quote_id: int, db: Session = Depends(get_db)) -> Quote:
    quote = db.get(Quote, quote_id)
    if quote is None:
        raise NotFound(f"Quote {quote_id} not found")
    return quote


@router.patch("/{quote_id}/line-items", response_model=QuoteRead)
def patch_line_items(
    quote_id: int, payload: QuoteLineItemsOverrideRequest, db: Session = Depends(get_db)
) -> Quote:
    overrides = [
        LineItemOverride(line_item_id=o.line_item_id, final_total=o.final_total) for o in payload.overrides
    ]
    return override_line_items(db, quote_id, overrides)


@router.post("/{quote_id}/send", response_model=QuoteRead)
def send(quote_id: int, db: Session = Depends(get_db)) -> Quote:
    """MVP behavior: marks the quote as sent only; no email or PDF is generated."""
    return send_quote(db, quote_id)


@router.post("/{quote_id}/accept", response_model=ShipmentRead)
def accept(quote_id: int, actor: str = Depends(current_actor), db: Session = Depends(get_db)):
    return accept_quote(db, quote_id, actor)
