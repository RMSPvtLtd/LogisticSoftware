"""Owns the Quote lifecycle: generation, manual overrides, sending, and
acceptance. `recalculate_totals` is the only place a Quote's subtotal,
markup_amount, and total are derived from its line items — nothing else
computes those fields.

Lifecycle:

    draft     -> may be edited, sent, or accepted (if not expired)
    sent      -> may be accepted (if not expired); may not be edited or re-sent
    accepted  -> terminal (repeated acceptance stays idempotent, see accept_quote)
    expired   -> terminal

A draft/sent quote whose valid_until has passed is treated as expired the
next time it is touched by one of these operations (`_apply_lazy_expiry`).
There is no scheduler; expiry is evaluated lazily, on demand.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import InvalidQuoteState, NotFound, QuoteExpired
from app.models.enums import EventSource, QuoteStatus, ReferenceType, ShipmentStage
from app.models.inquiry import Inquiry
from app.models.quote import Quote, QuoteLineItem
from app.models.shipment import Shipment, ShipmentReference, StatusEvent
from app.services.pricing import price_inquiry
from app.services.shipments import allocate_job_number

CENTS = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def _get_quote(session: Session, quote_id: int) -> Quote:
    quote = session.get(Quote, quote_id)
    if quote is None:
        raise NotFound(f"Quote {quote_id} not found")
    return quote


def _apply_lazy_expiry(quote: Quote, today: date) -> None:
    if quote.status in (QuoteStatus.DRAFT, QuoteStatus.SENT) and quote.valid_until < today:
        quote.status = QuoteStatus.EXPIRED


def recalculate_totals(quote: Quote) -> None:
    """The only place Quote.subtotal / markup_amount / total are computed.
    Uses each line item's final_total — which equals calculated_total unless
    a pricing user overrode it — as the authoritative line amount.
    """
    settings = get_settings()
    subtotal = _money(sum((li.final_total for li in quote.line_items), Decimal("0")))
    markup_amount = _money(subtotal * settings.default_markup_percent / Decimal("100"))
    quote.subtotal = subtotal
    quote.markup_amount = markup_amount
    quote.total = _money(subtotal + markup_amount)


def generate_quote(session: Session, inquiry_id: int, *, today: date | None = None) -> Quote:
    today = today or date.today()
    inquiry = session.get(Inquiry, inquiry_id)
    if inquiry is None:
        raise NotFound(f"Inquiry {inquiry_id} not found")

    settings = get_settings()
    priced = price_inquiry(session, inquiry, today=today)

    quote = Quote(
        inquiry_id=inquiry.id,
        status=QuoteStatus.DRAFT,
        currency=priced.currency,
        valid_until=today + timedelta(days=settings.quote_validity_days),
    )
    for line in priced.line_items:
        quote.line_items.append(
            QuoteLineItem(
                kind=line.kind,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                calculated_total=line.calculated_total,
                final_total=line.calculated_total,
                markup_amount=line.markup_amount,
                is_manual_override=False,
            )
        )
    recalculate_totals(quote)

    session.add(quote)
    session.flush()
    return quote


@dataclass(frozen=True)
class LineItemOverride:
    line_item_id: int
    final_total: Decimal


def override_line_items(
    session: Session, quote_id: int, overrides: list[LineItemOverride], *, today: date | None = None
) -> Quote:
    today = today or date.today()
    quote = _get_quote(session, quote_id)
    _apply_lazy_expiry(quote, today)

    if quote.status != QuoteStatus.DRAFT:
        raise InvalidQuoteState(f"Quote {quote.id} cannot be edited from status {quote.status.value}")

    line_items_by_id = {li.id: li for li in quote.line_items}
    for override in overrides:
        line_item = line_items_by_id.get(override.line_item_id)
        if line_item is None:
            raise NotFound(f"Line item {override.line_item_id} not found on quote {quote_id}")
        # quantity, unit_price, and calculated_total are untouched — the
        # original pricing calculation is preserved for reference.
        line_item.final_total = _money(override.final_total)
        line_item.is_manual_override = True

    recalculate_totals(quote)
    session.flush()
    return quote


def send_quote(session: Session, quote_id: int, *, today: date | None = None) -> Quote:
    """MVP behavior: marks the quote as sent only; no email or PDF is generated."""
    today = today or date.today()
    quote = _get_quote(session, quote_id)
    _apply_lazy_expiry(quote, today)

    if quote.status != QuoteStatus.DRAFT:
        raise InvalidQuoteState(f"Quote {quote.id} cannot be sent from status {quote.status.value}")

    quote.status = QuoteStatus.SENT
    session.flush()
    return quote


def accept_quote(session: Session, quote_id: int, actor: str, *, today: date | None = None) -> Shipment:
    """Transactional and idempotent. Raises without mutating anything on an
    expired or inconsistent quote. Does not commit — the caller's
    transaction boundary decides when this becomes durable, which is what
    lets a failure anywhere in this function roll back the quote status
    change, the job number counter increment, and the shipment together.
    """
    today = today or date.today()

    # Row-locked on PostgreSQL (see services.shipments._lock_counter_row for
    # why SQLite doesn't need the equivalent here).
    stmt = select(Quote).where(Quote.id == quote_id)
    if session.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    quote = session.execute(stmt).scalar_one_or_none()
    if quote is None:
        raise NotFound(f"Quote {quote_id} not found")

    existing_shipment = session.execute(
        select(Shipment).where(Shipment.quote_id == quote.id)
    ).scalar_one_or_none()
    if existing_shipment is not None:
        # Idempotent: a quote already accepted (with its shipment intact)
        # returns that shipment rather than creating a second one.
        return existing_shipment

    _apply_lazy_expiry(quote, today)

    if quote.status == QuoteStatus.EXPIRED:
        raise QuoteExpired(f"Quote {quote.id} expired on {quote.valid_until}")
    if quote.status == QuoteStatus.ACCEPTED:
        # status=accepted but no shipment was found above: an inconsistent
        # state that must be rejected rather than silently opening a second job.
        raise InvalidQuoteState(f"Quote {quote.id} is already accepted but has no shipment")
    if quote.status not in (QuoteStatus.DRAFT, QuoteStatus.SENT):
        raise InvalidQuoteState(f"Quote {quote.id} cannot be accepted from status {quote.status.value}")

    quote.status = QuoteStatus.ACCEPTED

    job_number = allocate_job_number(session, today.year)
    shipment = Shipment(
        customer_id=quote.inquiry.customer_id,
        inquiry_id=quote.inquiry_id,
        quote_id=quote.id,
        job_number=job_number,
        stage=ShipmentStage.JOB_OPENED,
    )
    session.add(shipment)
    session.flush()  # assigns shipment.id for the reference/event below

    shipment.references.append(ShipmentReference(type=ReferenceType.JOB_NUMBER, value=job_number))
    shipment.status_events.append(
        StatusEvent(
            stage=ShipmentStage.JOB_OPENED,
            actor=actor,
            note="Job opened from accepted quote.",
            source=EventSource.SYSTEM,
            is_stage_change=True,
        )
    )
    session.flush()
    return shipment
