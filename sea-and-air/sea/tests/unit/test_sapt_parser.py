import pytest

from integrations.tracking.sapt import (
    _build_result,
    _extract_data_object,
    _extract_records,
    _parse_sapt_timestamp,
)
from utils.errors import ProviderResponseInvalid
from conftest import fixture_html


def test_extract_data_object_from_valid_response():
    html = fixture_html("sapt_container_history_valid.html")
    data_object = _extract_data_object(html)
    assert data_object["gridName"] == "ContainerHistory"
    assert data_object["isSuccess"] is True
    assert isinstance(data_object["_jsonArray"], str)


def test_extract_data_object_fails_gracefully_on_malformed_html():
    html = fixture_html("sapt_container_history_malformed.html")
    with pytest.raises(ProviderResponseInvalid):
        _extract_data_object(html)


def test_extract_records_missing_jsonarray_fails_gracefully():
    html = fixture_html("sapt_container_history_missing_jsonarray.html")
    data_object = _extract_data_object(html)
    with pytest.raises(ProviderResponseInvalid):
        _extract_records(data_object)


def test_extract_records_invalid_json_fails_gracefully():
    html = fixture_html("sapt_container_history_invalid_json.html")
    data_object = _extract_data_object(html)
    with pytest.raises(ProviderResponseInvalid):
        _extract_records(data_object)


def test_extract_records_empty_array():
    html = fixture_html("sapt_container_history_empty_array.html")
    data_object = _extract_data_object(html)
    assert _extract_records(data_object) == []


def test_extract_records_valid_response_returns_two_records():
    html = fixture_html("sapt_container_history_valid.html")
    data_object = _extract_data_object(html)
    records = _extract_records(data_object)
    assert len(records) == 2
    assert records[0]["CONTAINER NO"] == "CAAU2314798"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("N/A", None),
        ("n/a", None),
        ("", None),
        ("not a date", None),
        ("08-AUG-26 10.22.33 AM", "2026-08-08T10:22:33"),
        ("23-JUL-26 08.55.55 AM", "2026-07-23T08:55:55"),
        ("18-JUL-26 10.59.04 AM", "2026-07-18T10:59:04"),
        ("01-JAN-26 12.00.00 AM", "2026-01-01T00:00:00"),  # 12 AM = midnight
        ("01-JAN-26 12.00.00 PM", "2026-01-01T12:00:00"),  # 12 PM = noon
        ("01-JAN-26 01.00.00 PM", "2026-01-01T13:00:00"),  # PM rollover
    ],
)
def test_parse_sapt_timestamp(raw, expected):
    result = _parse_sapt_timestamp(raw)
    if expected is None:
        assert result is None
    else:
        assert result.isoformat() == expected
