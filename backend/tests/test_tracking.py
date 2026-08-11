from datetime import date

import pytest

import app.models as m
from app.errors import AmbiguousTrackingReference, NotFound
from app.models.enums import EventSource, ReferenceType, ShipmentStage, TransportMode, stage_group, stage_label
from app.schemas.tracking import from_shipment
from app.services.quotes import accept_quote, generate_quote
from app.services.tracking import find_shipment_for_tracking
from app.services.transitions import advance_stage, record_note, set_risk
from tests.factories import make_customer, make_inquiry, simple_rate_card

TODAY = date(2026, 6, 1)


def _accepted_shipment(db_session, **inquiry_overrides):
    customer = make_customer(db_session)
    simple_rate_card(db_session, mode=inquiry_overrides.get("mode", TransportMode.AIR))
    inquiry = make_inquiry(db_session, customer, **inquiry_overrides)
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
    advance_stage(db_session, shipment, ShipmentStage.GD, actor="ops", note=None, source=EventSource.MANUAL)
    advance_stage(db_session, shipment, ShipmentStage.PICKUP, actor="ops", note="picked up", source=EventSource.MANUAL)

    result = from_shipment(shipment)
    statuses = {item.stage: item.status for item in result.checklist}

    assert statuses[ShipmentStage.INQUIRY] == "completed"
    assert statuses[ShipmentStage.QUOTATION] == "completed"
    assert statuses[ShipmentStage.JOB_OPENING] == "completed"
    assert statuses[ShipmentStage.AIRWAY_BILL] == "completed"
    assert statuses[ShipmentStage.GD] == "completed"
    assert statuses[ShipmentStage.PICKUP] == "current"
    assert statuses[ShipmentStage.GATE_IN] == "upcoming"
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
    advance_stage(db_session, shipment, ShipmentStage.GD, actor="ops", note="b", source=EventSource.MANUAL)

    result = from_shipment(shipment)

    assert [e.stage for e in result.status_history] == [
        ShipmentStage.INQUIRY, ShipmentStage.QUOTATION, ShipmentStage.JOB_OPENING,
        ShipmentStage.AIRWAY_BILL, ShipmentStage.GD,
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


# --- mode-aware labels/groups ---
#
# Sea walks the identical OPERATIONAL_STAGE_ORDER as air (see
# test_transitions.py) -- only the display text for one stage and two
# groups differs. Air's output must stay exactly what it was before mode
# was a parameter.


def test_air_stage_labels_and_groups_unchanged():
    assert stage_label(ShipmentStage.AIRWAY_BILL, TransportMode.AIR) == "Airway Bill"
    assert stage_group(ShipmentStage.GATE_IN, TransportMode.AIR) == "Airport"
    assert stage_group(ShipmentStage.DEPARTURE, TransportMode.AIR) == "Airline"
    # No mode passed at all -- the pre-existing call shape -- must still work.
    assert stage_label(ShipmentStage.AIRWAY_BILL) == "Airway Bill"
    assert stage_group(ShipmentStage.GATE_IN) == "Airport"


def test_sea_stage_labels_and_groups_differ_from_air():
    assert stage_label(ShipmentStage.AIRWAY_BILL, TransportMode.SEA) == "Bill of Lading"
    assert stage_group(ShipmentStage.GATE_IN, TransportMode.SEA) == "Port"
    assert stage_group(ShipmentStage.DEPARTURE, TransportMode.SEA) == "Carrier"
    # Stages with no override fall back to the shared label/group unchanged.
    assert stage_label(ShipmentStage.CUSTOMS_CLEARANCE, TransportMode.SEA) == "Customs Clearance"


def test_meta_stages_endpoint_is_mode_aware(client):
    air_response = client.get("/meta/stages")
    sea_response = client.get("/meta/stages?mode=sea")
    assert air_response.status_code == 200
    assert sea_response.status_code == 200

    air_stages = {s["stage"]: s for s in air_response.json()["stages"]}
    sea_stages = {s["stage"]: s for s in sea_response.json()["stages"]}

    assert air_stages["airway_bill"]["label"] == "Airway Bill"
    assert air_stages["gate_in"]["group"] == "Airport"
    assert sea_stages["airway_bill"]["label"] == "Bill of Lading"
    assert sea_stages["gate_in"]["group"] == "Port"
    # Same stage keys, same order, in both modes.
    assert list(air_stages.keys()) == list(sea_stages.keys())


def test_sea_shipment_checklist_uses_sea_mode(db_session):
    shipment = _accepted_shipment(db_session, mode=TransportMode.SEA)
    result = from_shipment(shipment)
    assert result.mode == TransportMode.SEA
