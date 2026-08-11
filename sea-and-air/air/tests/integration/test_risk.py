from datetime import date

from models.enums import EventSource
from services.quotes import accept_quote, generate_quote
from services.transitions import set_risk
from factories import make_customer, make_inquiry, simple_rate_card

TODAY = date(2026, 6, 1)


def _accepted_shipment(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    return accept_quote(db_session, quote.id, "ops", today=TODAY)


def test_set_risk(db_session):
    shipment = _accepted_shipment(db_session)
    set_risk(db_session, shipment, is_at_risk=True, risk_reason="Carrier missed departure", actor="ops")

    assert shipment.is_at_risk is True
    assert shipment.risk_reason == "Carrier missed departure"


def test_clear_risk(db_session):
    shipment = _accepted_shipment(db_session)
    set_risk(db_session, shipment, is_at_risk=True, risk_reason="Delayed", actor="ops")
    set_risk(db_session, shipment, is_at_risk=False, risk_reason=None, actor="ops")

    assert shipment.is_at_risk is False
    assert shipment.risk_reason is None


def test_risk_change_creates_internal_history_event(db_session):
    shipment = _accepted_shipment(db_session)
    n_before = len(shipment.status_events)
    stage_before = shipment.stage

    set_risk(db_session, shipment, is_at_risk=True, risk_reason="Customs docs pending", actor="ops")

    assert len(shipment.status_events) == n_before + 1
    event = shipment.status_events[-1]
    assert event.source == EventSource.SYSTEM
    assert event.is_internal is True
    assert event.is_stage_change is False
    assert shipment.stage == stage_before  # risk change never touches stage


def test_tracking_exposes_only_at_risk_boolean(db_session):
    from schemas.tracking import from_shipment

    shipment = _accepted_shipment(db_session)
    set_risk(db_session, shipment, is_at_risk=True, risk_reason="Very sensitive internal detail", actor="ops")

    result = from_shipment(shipment)

    assert result.at_risk is True
    assert "risk_reason" not in result.model_dump()
    assert "Very sensitive internal detail" not in result.model_dump_json()
