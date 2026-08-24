"""Owns the Quote lifecycle: generation/revisioning, manual overrides,
sending, acceptance, and rejection. `recalculate_totals` is the only place a
Quote's subtotal, markup_amount, and total are derived from its line items —
nothing else computes those fields.

Status lifecycle (send/accept/reject only, not line-item editing):

    draft     -> may be sent, accepted, or rejected (if not expired)
    sent      -> may be accepted or rejected (if not expired); may not be re-sent
    accepted  -> terminal (repeated acceptance stays idempotent, see accept_quote)
    expired   -> terminal
    rejected  -> terminal

A draft/sent quote whose valid_until has passed is treated as expired the
next time it is touched by one of these operations (`_apply_lazy_expiry`).
There is no scheduler; expiry is evaluated lazily, on demand.

Revisions: re-generating a quote for an inquiry that already has a
draft/sent/rejected/expired quote does not touch that old row -- it marks it
`superseded_at` and creates a new Quote sharing the same `root_quote_id` with
`revision_number + 1` (see `generate_quote`). A superseded quote is
permanently frozen: `send_quote`/`accept_quote`/`reject_quote`/
`override_line_items`/`set_quote_adjustments` all refuse to act on one. An
inquiry whose current quote is already `accepted` cannot be re-quoted at all
(see `generate_quote`) -- a job is already open from it.

Line-item editing (`override_line_items`) is independent of quote status --
it's gated on the *shipment's* stage instead (see that function's
docstring): pricing can be corrected any time up until the shipment is
invoiced to the customer, not just while the quote is still a draft.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_settings
from utils.errors import InvalidMoneyAmount, InvalidQuoteState, NotFound, QuoteExpired
from models.enums import EventSource, QuoteStatus, ReferenceType, ShipmentStage
from models.inquiry import Inquiry
from models.quote import Quote, QuoteLineItem
from models.shipment import Shipment, ShipmentReference
from schemas.money import MAX_MONEY
from services.pricing import price_inquiry
from services.shipments import allocate_job_number
from services.transitions import advance_stage, record_note

CENTS = Decimal("0.01")


def _quote_ref(quote: Quote) -> str:
    """Human-readable revision reference for audit notes and PDFs, e.g.
    'Q-12 Rev 2'. root_quote_id is null on the root quote itself."""
    return f"Q-{quote.root_quote_id or quote.id} Rev {quote.revision_number}"


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


def _assert_not_superseded(quote: Quote) -> None:
    """A superseded revision (see `generate_quote`) is permanently frozen --
    its `status` field may still read draft/sent from before it was
    superseded, so this is a separate check, not implied by status alone."""
    if quote.superseded_at is not None:
        raise InvalidQuoteState(
            f"{_quote_ref(quote)} has been superseded by a later revision and can no longer be acted on"
        )


def list_revisions(session: Session, quote_id: int) -> list[Quote]:
    """Every quote sharing `quote`'s revision family (including itself),
    oldest first -- the full, permanently auditable history of an inquiry's
    quote."""
    quote = _get_quote(session, quote_id)
    root_id = quote.root_quote_id or quote.id
    stmt = (
        select(Quote)
        .where((Quote.id == root_id) | (Quote.root_quote_id == root_id))
        .order_by(Quote.revision_number)
    )
    return list(session.execute(stmt).scalars())


def recalculate_totals(quote: Quote) -> None:
    """The only place Quote.subtotal / markup_amount / total are computed.
    Uses each line item's final_total — which equals calculated_total unless
    a pricing user overrode it — as the authoritative line amount.
    tax_amount/discount_amount are flat, ops-entered amounts (default zero,
    untouched here) rather than derived, so they're simply folded into total.

    Never trusts a client-supplied total: nothing here reads a total off a
    request, and no caller is able to set one — the value is always derived
    from stored line items. Raises rather than producing a negative total
    (see `_assert_total_is_sane`).
    """
    settings = get_settings()
    subtotal = _money(sum((li.final_total for li in quote.line_items), Decimal("0")))
    markup_amount = _money(subtotal * settings.default_markup_percent / Decimal("100"))
    total = _money(subtotal + markup_amount + quote.tax_amount - quote.discount_amount)
    _assert_total_is_sane(total)

    quote.subtotal = subtotal
    quote.markup_amount = markup_amount
    quote.total = total


def _assert_total_is_sane(total: Decimal) -> None:
    """A discount larger than the quote's value would otherwise produce a
    negative total -- an invoice that owes the customer money. Per-field
    validation can't catch this: each individual amount is within range, it's
    only their combination that's invalid, so the check has to live here
    where the arithmetic actually happens (and therefore covers every caller,
    including the seed script and any future one).
    """
    if total < 0:
        raise InvalidMoneyAmount(
            "Adjustments would make the quote total negative; "
            "the discount cannot exceed the quote's subtotal, markup and tax combined."
        )
    if total > MAX_MONEY:
        raise InvalidMoneyAmount(f"Quote total would exceed the maximum supported amount ({MAX_MONEY}).")


def generate_quote(session: Session, inquiry_id: int, *, today: date | None = None) -> Quote:
    today = today or date.today()
    inquiry = session.get(Inquiry, inquiry_id)
    if inquiry is None:
        raise NotFound(f"Inquiry {inquiry_id} not found")
    if inquiry.shipment is None:
        # Every Inquiry gets a Shipment row at creation (services.inquiries) --
        # this would only be missing for data created before that existed.
        raise NotFound(f"Inquiry {inquiry_id} has no tracking record")

    # Row-locked on PostgreSQL so a concurrent accept_quote on the same
    # inquiry can't race with this repointing quote_id underneath it.
    shipment_stmt = select(Shipment).where(Shipment.id == inquiry.shipment.id)
    if session.bind.dialect.name == "postgresql":
        shipment_stmt = shipment_stmt.with_for_update()
    shipment = session.execute(shipment_stmt).scalar_one()

    old_quote: Quote | None = None
    if shipment.quote_id is not None:
        old_quote = session.get(Quote, shipment.quote_id)
        if old_quote is not None and old_quote.status == QuoteStatus.ACCEPTED:
            # Fixes a latent bug: this used to silently repoint quote_id away
            # from a quote that already has an open job. Once accepted, an
            # inquiry can never be re-quoted -- file a new inquiry instead.
            raise InvalidQuoteState(
                f"Inquiry {inquiry_id} already has an accepted quote ({_quote_ref(old_quote)}) "
                "with an open job; it cannot be re-quoted"
            )

    settings = get_settings()
    priced = price_inquiry(session, inquiry, today=today)

    quote = Quote(
        inquiry_id=inquiry.id,
        status=QuoteStatus.DRAFT,
        currency=priced.currency,
        valid_until=today + timedelta(days=settings.quote_validity_days),
        tax_amount=Decimal("0"),
        discount_amount=Decimal("0"),
        revision_number=(old_quote.revision_number + 1) if old_quote else 1,
        root_quote_id=(old_quote.root_quote_id or old_quote.id) if old_quote else None,
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

    if old_quote is not None:
        # A revision: freeze the old row permanently rather than mutating it.
        old_quote.superseded_at = datetime.now(timezone.utc)
        record_note(
            session, shipment, actor="system",
            note=f"{_quote_ref(quote)} created, superseding {_quote_ref(old_quote)}.",
            source=EventSource.SYSTEM, is_internal=True,
        )

    shipment.quote_id = quote.id
    if shipment.stage == ShipmentStage.INQUIRY:
        # First quote for this inquiry -> advance the tracking record.
        # Re-quoting later (revisions) just repoints quote_id above without
        # moving the stage again.
        advance_stage(
            session, shipment, ShipmentStage.QUOTATION,
            actor="system", note=f"Quote #{quote.id} generated.", source=EventSource.SYSTEM,
        )
    session.flush()
    return quote


@dataclass(frozen=True)
class LineItemOverride:
    line_item_id: int
    final_total: Decimal


def override_line_items(
    session: Session, quote_id: int, overrides: list[LineItemOverride], *, today: date | None = None
) -> Quote:
    """Editable regardless of quote status (draft/sent/accepted/expired) --
    only blocked once the quote's shipment has reached its terminal stage,
    invoice_to_customer. A quote with no shipment reference (superseded by a
    later re-quote, see `generate_quote`) has nothing that can have "ended",
    so it stays editable.
    """
    today = today or date.today()
    quote = _get_quote(session, quote_id)
    _apply_lazy_expiry(quote, today)
    _assert_not_superseded(quote)

    if quote.shipment is not None and quote.shipment.stage == ShipmentStage.INVOICE_TO_CUSTOMER:
        raise InvalidQuoteState(f"Quote {quote.id} cannot be edited: its shipment has already been invoiced")

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


def set_quote_adjustments(
    session: Session, quote_id: int, *, tax_amount: Decimal, discount_amount: Decimal, today: date | None = None
) -> Quote:
    """Set the quote's flat tax/discount amounts. Same editability rule as
    override_line_items -- blocked only once the shipment has been invoiced.
    """
    today = today or date.today()
    quote = _get_quote(session, quote_id)
    _apply_lazy_expiry(quote, today)
    _assert_not_superseded(quote)

    if quote.shipment is not None and quote.shipment.stage == ShipmentStage.INVOICE_TO_CUSTOMER:
        raise InvalidQuoteState(f"Quote {quote.id} cannot be edited: its shipment has already been invoiced")

    quote.tax_amount = _money(tax_amount)
    quote.discount_amount = _money(discount_amount)
    recalculate_totals(quote)
    session.flush()
    return quote


def send_quote(session: Session, quote_id: int, *, today: date | None = None) -> Quote:
    """MVP behavior: marks the quote as sent only; no email or PDF is generated."""
    today = today or date.today()
    quote = _get_quote(session, quote_id)
    _apply_lazy_expiry(quote, today)
    _assert_not_superseded(quote)

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
    change, the job number counter increment, and the shipment stage
    transition together.

    The Shipment already exists (created with the Inquiry — see
    services.inquiries.create_inquiry) and was moved to QUOTATION when this
    quote was generated; accepting advances that same row to JOB_OPENING and
    assigns its job number, rather than creating a new row.
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

    shipment = session.execute(
        select(Shipment).where(Shipment.inquiry_id == quote.inquiry_id)
    ).scalar_one_or_none()
    if shipment is None:
        raise NotFound(f"Inquiry {quote.inquiry_id} has no tracking record")

    if shipment.job_number is not None:
        # Idempotent: a quote already accepted (job number already assigned)
        # returns the existing shipment rather than re-processing.
        if shipment.quote_id == quote.id:
            return shipment
        raise InvalidQuoteState(
            f"Inquiry {quote.inquiry_id} already has an open job from a different quote"
        )

    _apply_lazy_expiry(quote, today)
    _assert_not_superseded(quote)

    if quote.status == QuoteStatus.EXPIRED:
        raise QuoteExpired(f"Quote {quote.id} expired on {quote.valid_until}")
    if quote.status == QuoteStatus.ACCEPTED:
        # status=accepted but the shipment has no job number: an inconsistent
        # state that must be rejected rather than silently opening a job.
        raise InvalidQuoteState(f"Quote {quote.id} is already accepted but its shipment has no job number")
    if quote.status not in (QuoteStatus.DRAFT, QuoteStatus.SENT):
        raise InvalidQuoteState(f"Quote {quote.id} cannot be accepted from status {quote.status.value}")

    quote.status = QuoteStatus.ACCEPTED

    job_number = allocate_job_number(session, today.year)
    shipment.quote_id = quote.id
    shipment.job_number = job_number

    advance_stage(
        session, shipment, ShipmentStage.JOB_OPENING,
        actor=actor, note="Job opened from accepted quote.", source=EventSource.SYSTEM,
    )
    shipment.references.append(ShipmentReference(type=ReferenceType.JOB_NUMBER, value=job_number))
    record_note(
        session, shipment, actor=actor,
        note=f"{_quote_ref(quote)} accepted.", source=EventSource.SYSTEM, is_internal=True,
    )
    session.flush()
    return shipment


def reject_quote(
    session: Session, quote_id: int, *, reason: str, actor: str, today: date | None = None
) -> Quote:
    """Ops-only rejection (see plan: the customer portal's quote page stays
    read-only). Same row-locking and lazy-expiry pattern as accept_quote, so
    a quote can't be rejected and accepted by two concurrent requests. Only
    valid from draft/sent -- an accepted quote can never "silently become
    rejected", and an already-rejected/expired quote is terminal (the way
    forward is a new revision via generate_quote, not un-rejecting this row).
    """
    today = today or date.today()
    if not reason or not reason.strip():
        raise InvalidQuoteState("A rejection reason is required")

    stmt = select(Quote).where(Quote.id == quote_id)
    if session.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    quote = session.execute(stmt).scalar_one_or_none()
    if quote is None:
        raise NotFound(f"Quote {quote_id} not found")

    _apply_lazy_expiry(quote, today)
    _assert_not_superseded(quote)

    if quote.status not in (QuoteStatus.DRAFT, QuoteStatus.SENT):
        raise InvalidQuoteState(f"Quote {quote.id} cannot be rejected from status {quote.status.value}")

    quote.status = QuoteStatus.REJECTED
    quote.rejected_reason = reason
    quote.rejected_by = actor
    quote.rejected_at = datetime.now(timezone.utc)

    if quote.shipment is not None:
        record_note(
            session, quote.shipment, actor=actor,
            note=f"{_quote_ref(quote)} rejected: {reason}", source=EventSource.SYSTEM, is_internal=True,
        )
    session.flush()
    return quote
