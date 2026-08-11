from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import select

import app.models as m
from app.errors import InvalidQuoteState, QuoteExpired
from app.models.enums import EventSource, QuoteStatus, ShipmentStage
from app.services.quotes import LineItemOverride, accept_quote, generate_quote, override_line_items, send_quote
from tests.factories import make_customer, make_inquiry, simple_rate_card

TODAY = date(2026, 6, 1)


def _quote(db_session, **inquiry_overrides):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer, **inquiry_overrides)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    return quote


# --- lifecycle ---


def test_generated_quote_starts_draft(db_session):
    from app.config import get_settings

    quote = _quote(db_session)
    assert quote.status == QuoteStatus.DRAFT
    assert quote.valid_until == TODAY + timedelta(days=get_settings().quote_validity_days)


def test_editing_sent_quote_is_rejected(db_session):
    quote = _quote(db_session)
    send_quote(db_session, quote.id, today=TODAY)

    line_item_id = quote.line_items[0].id
    with pytest.raises(InvalidQuoteState):
        override_line_items(db_session, quote.id, [LineItemOverride(line_item_id, Decimal("1"))], today=TODAY)


def test_sending_accepted_quote_is_rejected(db_session):
    quote = _quote(db_session)
    send_quote(db_session, quote.id, today=TODAY)
    accept_quote(db_session, quote.id, "ops", today=TODAY)

    with pytest.raises(InvalidQuoteState):
        send_quote(db_session, quote.id, today=TODAY)


def test_resending_draft_after_send_is_rejected(db_session):
    quote = _quote(db_session)
    send_quote(db_session, quote.id, today=TODAY)

    with pytest.raises(InvalidQuoteState):
        send_quote(db_session, quote.id, today=TODAY)


def test_accepting_expired_quote_is_rejected_and_status_persisted(db_session):
    quote = _quote(db_session)
    much_later = TODAY + timedelta(days=365)

    with pytest.raises(QuoteExpired):
        accept_quote(db_session, quote.id, "ops", today=much_later)
    assert quote.status == QuoteStatus.EXPIRED


def test_lazy_expiry_blocks_edit(db_session):
    quote = _quote(db_session)
    much_later = TODAY + timedelta(days=365)
    line_item_id = quote.line_items[0].id

    with pytest.raises(InvalidQuoteState):
        override_line_items(
            db_session, quote.id, [LineItemOverride(line_item_id, Decimal("1"))], today=much_later
        )
    assert quote.status == QuoteStatus.EXPIRED


# --- override ---


def test_override_preserves_calculated_total_and_changes_final_total(db_session):
    quote = _quote(db_session, weight_kg=Decimal("100"), volume_cbm=Decimal("0.01"))
    line_item = quote.line_items[0]
    original_calculated = line_item.calculated_total
    original_quantity = line_item.quantity
    original_unit_price = line_item.unit_price

    updated = override_line_items(
        db_session, quote.id, [LineItemOverride(line_item.id, Decimal("1"))], today=TODAY
    )

    updated_line = next(li for li in updated.line_items if li.id == line_item.id)
    assert updated_line.final_total == Decimal("1.00")
    assert updated_line.calculated_total == original_calculated
    assert updated_line.quantity == original_quantity
    assert updated_line.unit_price == original_unit_price
    assert updated_line.is_manual_override is True


def test_override_recalculates_quote_total(db_session):
    quote = _quote(db_session)
    original_total = quote.total
    line_item = quote.line_items[0]

    updated = override_line_items(
        db_session, quote.id, [LineItemOverride(line_item.id, Decimal("1"))], today=TODAY
    )

    assert updated.total != original_total
    expected_subtotal = sum((li.final_total for li in updated.line_items), Decimal("0"))
    assert updated.subtotal == expected_subtotal


# --- acceptance ---


def test_accept_sets_status_and_creates_shipment_with_relationships(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()

    shipment = accept_quote(db_session, quote.id, "ops", today=TODAY)

    assert quote.status == QuoteStatus.ACCEPTED
    assert shipment.customer_id == customer.id
    assert shipment.inquiry_id == inquiry.id
    assert shipment.quote_id == quote.id
    assert shipment.stage == ShipmentStage.JOB_OPENING


def test_accept_generates_correctly_formatted_job_number(db_session):
    quote = _quote(db_session)
    shipment = accept_quote(db_session, quote.id, "ops", today=TODAY)
    assert shipment.job_number == "RAZ-2026-00001"


def test_accept_job_number_increments_across_quotes(db_session):
    q1 = _quote(db_session)
    q2 = _quote(db_session)
    s1 = accept_quote(db_session, q1.id, "ops", today=TODAY)
    s2 = accept_quote(db_session, q2.id, "ops", today=TODAY)
    assert s1.job_number == "RAZ-2026-00001"
    assert s2.job_number == "RAZ-2026-00002"


def test_accept_creates_initial_job_opening_event(db_session):
    quote = _quote(db_session)
    shipment = accept_quote(db_session, quote.id, "ops", today=TODAY)

    # inquiry -> quotation events already exist from create_inquiry /
    # generate_quote; accept_quote adds the job_opening event on top.
    assert [e.stage for e in shipment.status_events] == [
        ShipmentStage.INQUIRY, ShipmentStage.QUOTATION, ShipmentStage.JOB_OPENING,
    ]
    event = shipment.status_events[-1]
    assert event.stage == ShipmentStage.JOB_OPENING
    assert event.source == EventSource.SYSTEM
    assert event.is_stage_change is True


def test_repeated_acceptance_is_idempotent(db_session):
    quote = _quote(db_session)
    first = accept_quote(db_session, quote.id, "ops", today=TODAY)
    second = accept_quote(db_session, quote.id, "ops", today=TODAY)

    assert first.id == second.id
    shipments = db_session.execute(select(m.Shipment)).scalars().all()
    assert len(shipments) == 1


def test_already_accepted_without_job_number_is_rejected(db_session):
    # Inconsistent state: quote says accepted, but its shipment was never
    # actually advanced to job_opening (no job_number assigned).
    quote = _quote(db_session)
    quote.status = QuoteStatus.ACCEPTED
    db_session.flush()

    with pytest.raises(InvalidQuoteState):
        accept_quote(db_session, quote.id, "ops", today=TODAY)


def test_forced_failure_rolls_back_and_preserves_job_number_sequence(db_session, session_factory):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.commit()  # quote + shipment-at-quotation creation is durable, as it would be from a prior request
    quote_id = quote.id
    shipment_id = inquiry.shipment.id

    # accept_quote's stage transition happens inside advance_stage
    # (services.transitions), which is where the StatusEvent for
    # job_opening actually gets constructed.
    with patch("app.services.transitions.StatusEvent", side_effect=RuntimeError("forced failure")):
        with pytest.raises(RuntimeError):
            accept_quote(db_session, quote_id, "ops", today=TODAY)
    db_session.rollback()

    reloaded_quote = db_session.get(m.Quote, quote_id)
    assert reloaded_quote.status == QuoteStatus.DRAFT
    reloaded_shipment = db_session.get(m.Shipment, shipment_id)
    assert reloaded_shipment.job_number is None
    assert reloaded_shipment.stage == ShipmentStage.QUOTATION
    counters = db_session.execute(select(m.JobNumberCounter)).scalars().all()
    assert counters == [] or counters[0].last_value == 0

    shipment = accept_quote(db_session, quote_id, "ops", today=TODAY)
    assert shipment.job_number == "RAZ-2026-00001", "failed attempt must not consume a sequence number"
