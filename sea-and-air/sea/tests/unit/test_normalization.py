"""Verifies the SAPT record fields -> TrackingResult mapping (Phase 4):
CONTAINER NO -> container_number, STATUS -> status_code, GATE In/Out TIME
-> Gate In/Out events, LOADING/DISCHARGING TIME -> Loading/Discharging
events, and that internal SAPT fields (pid, formatter) never surface.
"""

from integrations.tracking.sapt import _build_result


def test_maps_known_fields_and_ignores_internal_ones():
    records = [
        {
            "CONTAINER NO": "CAAU2314798",
            "pid": "20411617",
            "STATUS": "XF",
            "GATE In TIME": "08-AUG-26 10.22.33 AM",
            "GATE OUT TIME": "N/A",
            "LOADING TIME": None,
            "DISCHARGING TIME": None,
            "formatter": "yes",
        }
    ]

    result = _build_result("CAAU2314798", records)

    assert result.provider == "SAPT"
    assert result.terminal == "South Asia Pakistan Terminals"
    assert result.container_number == "CAAU2314798"
    assert result.status_code == "XF"
    assert len(result.events) == 1
    assert result.events[0].type == "Gate In"
    assert result.events[0].timestamp == "2026-08-08T10:22:33"
    # pid/formatter must never leak into the normalized model.
    dumped = result.model_dump()
    assert "pid" not in dumped
    assert "formatter" not in dumped


def test_multiple_records_merge_into_one_result_sorted_most_recent_first():
    records = [
        {
            "CONTAINER NO": "CAAU2314798",
            "pid": "20411617",
            "STATUS": "XF",
            "GATE In TIME": "08-AUG-26 10.22.33 AM",
            "GATE OUT TIME": "N/A",
            "LOADING TIME": None,
            "DISCHARGING TIME": None,
            "formatter": "yes",
        },
        {
            "CONTAINER NO": "CAAU2314798",
            "pid": "20260519",
            "STATUS": "IF",
            "GATE In TIME": "N/A",
            "GATE OUT TIME": "23-JUL-26 08.55.55 AM",
            "LOADING TIME": None,
            "DISCHARGING TIME": "18-JUL-26 10.59.04 AM",
            "formatter": "yes",
        },
    ]

    result = _build_result("CAAU2314798", records)

    # Overall status comes from whichever record's own latest event is most
    # recent overall -- here that's the Aug 8 Gate In record (XF), not
    # simply "the first record in the array".
    assert result.status_code == "XF"

    event_types_in_order = [e.type for e in result.events]
    assert event_types_in_order == ["Gate In", "Gate Out", "Discharging"]
    timestamps = [e.timestamp for e in result.events]
    assert timestamps == sorted(timestamps, reverse=True)


def test_falls_back_to_requested_container_number_when_field_missing():
    records = [{"STATUS": "XF", "GATE In TIME": "08-AUG-26 10.22.33 AM"}]
    result = _build_result("CAAU2314798", records)
    assert result.container_number == "CAAU2314798"


def test_no_usable_fields_produces_empty_result():
    records = [{"container_no": "N/A", "formatter": "yes"}]
    result = _build_result("ZZZZ0000000", records)
    assert result.status_code is None
    assert result.events == []
