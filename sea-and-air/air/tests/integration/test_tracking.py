from datetime import date

import pytest

import models as m
from utils.errors import AmbiguousTrackingReference, NotFound
from models.enums import EventSource, ReferenceType, ShipmentStage
from schemas.tracking import from_shipment
from services.quotes import accept_quote, generate_quote
from services.tracking import find_shipment_for_tracking
from services.transitions import advance_stage, record_note, set_risk
from factories import make_customer, make_inquiry, simple_rate_card

TODAY = date(2026, 6, 1)


def _accepted_shipment(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    return accept_quote(db_session, quote.id, "ops", today=TODAY)


def _add_reference(db_session, shipment, ref_type, value):
    shipment.references.append(m.ShipmentReference(type=ref_type, value=value))
    db_session.flush()


# --- lookup ---


def test_lookup_by_job_number(db_session):
    shipment = _accepted_shipment(db_session)
    found = find_shipment_for_tracking(db_session, shipment.job_number)
    assert found.id == shipment.id


def test_lookup_by_container(db_session):
    shipment = _accepted_shipment(db_session)
    _add_reference(db_session, shipment, ReferenceType.CONTAINER, "MSKU1234567")

    found = find_shipment_for_tracking(db_session, "MSKU1234567")
    assert found.id == shipment.id


def test_lookup_by_mawb(db_session):
    shipment = _accepted_shipment(db_session)
    _add_reference(db_session, shipment, ReferenceType.MAWB, "176-12345678")

    found = find_shipment_for_tracking(db_session, "176-12345678")
    assert found.id == shipment.id


def test_lookup_by_hawb(db_session):
    shipment = _accepted_shipment(db_session)
    _add_reference(db_session, shipment, ReferenceType.HAWB, "HAWB-998877")

    found = find_shipment_for_tracking(db_session, "HAWB-998877")
    assert found.id == shipment.id


def test_lookup_no_match_raises_not_found(db_session):
    _accepted_shipment(db_session)
    with pytest.raises(NotFound):
        find_shipment_for_tracking(db_session, "NO-SUCH-REFERENCE")


def test_ambiguous_reference_raises_conflict_not_arbitrary_pick(db_session):
    shipment_a = _accepted_shipment(db_session)
    shipment_b = _accepted_shipment(db_session)
    # Two different shipments legitimately sharing the same container number
    # over time -- the lookup must refuse to guess.
    _add_reference(db_session, shipment_a, ReferenceType.CONTAINER, "SHARED-REF")
    _add_reference(db_session, shipment_b, ReferenceType.CONTAINER, "SHARED-REF")

    with pytest.raises(AmbiguousTrackingReference):
        find_shipment_for_tracking(db_session, "SHARED-REF")


# --- checklist / history / leakage ---


def test_checklist_states_for_mid_lifecycle_shipment(db_session):
    shipment = _accepted_shipment(db_session)
    advance_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", note=None, source=EventSource.MANUAL)
    advance_stage(db_session, shipment, ShipmentStage.PICKUP, actor="ops", note=None, source=EventSource.MANUAL)
    advance_stage(db_session, shipment, ShipmentStage.GATE_IN, actor="ops", note="gated in", source=EventSource.MANUAL)

    result = from_shipment(shipment)
    statuses = {item.stage: item.status for item in result.checklist}

    assert statuses[ShipmentStage.INQUIRY] == "completed"
    assert statuses[ShipmentStage.QUOTATION] == "completed"
    assert statuses[ShipmentStage.JOB_OPENING] == "completed"
    assert statuses[ShipmentStage.AIRWAY_BILL] == "completed"
    assert statuses[ShipmentStage.PICKUP] == "completed"
    assert statuses[ShipmentStage.GATE_IN] == "current"
    assert statuses[ShipmentStage.SHIPMENT_RECEIPT] == "upcoming"
    assert statuses[ShipmentStage.GD] == "upcoming"
    assert statuses[ShipmentStage.INVOICE_TO_CUSTOMER] == "upcoming"


def test_checklist_items_carry_a_completion_timestamp(db_session):
    shipment = _accepted_shipment(db_session)
    advance_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", note=None, source=EventSource.MANUAL)

    result = from_shipment(shipment)
    by_stage = {item.stage: item for item in result.checklist}

    assert by_stage[ShipmentStage.INQUIRY].timestamp is not None
    assert by_stage[ShipmentStage.JOB_OPENING].timestamp is not None
    assert by_stage[ShipmentStage.AIRWAY_BILL].timestamp is not None  # current stage
    assert by_stage[ShipmentStage.GD].timestamp is None  # not reached yet
    assert by_stage[ShipmentStage.INQUIRY].timestamp <= by_stage[ShipmentStage.JOB_OPENING].timestamp
    assert by_stage[ShipmentStage.JOB_OPENING].timestamp <= by_stage[ShipmentStage.AIRWAY_BILL].timestamp


def test_history_is_complete_and_chronological(db_session):
    shipment = _accepted_shipment(db_session)
    advance_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", note="a", source=EventSource.MANUAL)
    advance_stage(db_session, shipment, ShipmentStage.PICKUP, actor="ops", note="b", source=EventSource.MANUAL)

    result = from_shipment(shipment)

    assert [e.stage for e in result.status_history] == [
        ShipmentStage.INQUIRY, ShipmentStage.QUOTATION, ShipmentStage.JOB_OPENING,
        ShipmentStage.AIRWAY_BILL, ShipmentStage.PICKUP,
    ]
    assert result.status_history == sorted(result.status_history, key=lambda e: e.timestamp)


def test_internal_notes_excluded_from_history(db_session):
    shipment = _accepted_shipment(db_session)
    record_note(db_session, shipment, actor="ops", note="Internal-only ops commentary", source=EventSource.MANUAL, is_internal=True)

    result = from_shipment(shipment)

    notes = [e.note for e in result.status_history]
    assert "Internal-only ops commentary" not in notes


def test_no_pricing_markup_or_totals_leak_through_tracking(db_session):
    shipment = _accepted_shipment(db_session)
    payload = from_shipment(shipment).model_dump_json()

    # Checked as JSON keys (`"field_name":`), not raw substrings -- a status
    # note is free-text prose ("...accepted quote.") and may legitimately
    # mention these words without leaking the corresponding pricing field.
    forbidden_keys = (
        "markup_amount", "subtotal", "total", "unit_price",
        "calculated_total", "final_total", "quote_id", "quote",
    )
    for key in forbidden_keys:
        assert f'"{key}":' not in payload, f"leaked forbidden field: {key}"


def test_risk_reason_never_in_tracking_response(db_session):
    shipment = _accepted_shipment(db_session)
    set_risk(db_session, shipment, is_at_risk=True, risk_reason="Secret internal ops detail", actor="ops")

    payload = from_shipment(shipment).model_dump_json()

    assert "risk_reason" not in payload
    assert "Secret internal ops detail" not in payload
    assert from_shipment(shipment).at_risk is True


def test_job_number_reference_not_duplicated_in_reference_list(db_session):
    shipment = _accepted_shipment(db_session)
    result = from_shipment(shipment)

    # job_number is already the top-level field; it shouldn't also appear
    # redundantly inside the references list.
    assert all(ref.type != ReferenceType.JOB_NUMBER for ref in result.references)
