"""End-to-end through the real API route (POST /api/tracking), with only
the outbound SAPT HTTP call mocked via pytest-httpx -- everything else
(validation, the provider, parsing, normalization, caching, error mapping)
runs for real. Uses the known Phase 12 test container, CAAU2314798.
"""

import httpx
import pytest

from conftest import fixture_html


def _mock_full_lookup(httpx_mock):
    """A complete CAAU2314798 lookup makes three outbound requests: one
    ContainerHistory GET, then one ContainerDetails POST per history record
    (two, for this container) -- registered in that order."""
    httpx_mock.add_response(text=fixture_html("sapt_container_history_valid.html"))
    httpx_mock.add_response(text=fixture_html("sapt_container_details_xf.html"))
    httpx_mock.add_response(text=fixture_html("sapt_container_details_if.html"))


def test_valid_container_returns_normalized_tracking_result(client, httpx_mock):
    _mock_full_lookup(httpx_mock)

    response = client.post("/api/tracking", json={"container_number": "CAAU2314798"})

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "SAPT"
    assert body["terminal"] == "South Asia Pakistan Terminals"
    assert body["container_number"] == "CAAU2314798"
    assert body["status_code"] == "XF"
    event_types = [e["type"] for e in body["events"]]
    assert event_types == ["Gate In", "Gate Out", "Discharging"]
    assert len(body["details"]) == 2
    assert body["details"][0]["status_code"] == "XF"
    assert body["details"][0]["commodity"] == "MADE UPS"
    assert body["details"][1]["status_code"] == "IF"
    assert body["details"][1]["commodity"] == "POLISHED MARBLE SLABS  HS CODE: 68022100"


def test_container_with_no_records_returns_404(client, httpx_mock):
    httpx_mock.add_response(text=fixture_html("sapt_container_history_not_found.html"))

    response = client.post("/api/tracking", json={"container_number": "ZZZZ0000000"})

    assert response.status_code == 404
    assert "detail" in response.json()


def test_invalid_container_number_never_reaches_sapt(client, httpx_mock):
    # No httpx_mock.add_response() registered -- if the provider were
    # somehow reached despite invalid input, pytest-httpx fails the test
    # for an unmatched real request, proving validation short-circuits
    # before any network call.
    response = client.post("/api/tracking", json={"container_number": "not-a-container"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Please enter a valid container number."


def test_malformed_sapt_response_returns_503_not_a_stack_trace(client, httpx_mock):
    httpx_mock.add_response(text=fixture_html("sapt_container_history_malformed.html"))

    response = client.post("/api/tracking", json={"container_number": "CAAU2314798"})

    assert response.status_code == 503
    body = response.json()
    assert "detail" in body
    # Never leak the raw provider HTML/response into the client-facing error.
    assert "<html>" not in body["detail"]


def test_sapt_timeout_returns_503(client, httpx_mock):
    httpx_mock.add_exception(httpx.TimeoutException("timed out"))

    response = client.post("/api/tracking", json={"container_number": "CAAU2314798"})

    assert response.status_code == 503


def test_sapt_connection_failure_returns_503(client, httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("connection refused"))

    response = client.post("/api/tracking", json={"container_number": "CAAU2314798"})

    assert response.status_code == 503


def test_one_failed_detail_fetch_does_not_fail_the_whole_lookup(client, httpx_mock):
    # History succeeds, and one of the two detail fetches fails outright --
    # the tracking result (status/events) must still come back successfully,
    # just with that one voyage's detail card missing rather than a 503 for
    # the whole request.
    httpx_mock.add_response(text=fixture_html("sapt_container_history_valid.html"))
    httpx_mock.add_exception(httpx.TimeoutException("timed out"))
    httpx_mock.add_response(text=fixture_html("sapt_container_details_if.html"))

    response = client.post("/api/tracking", json={"container_number": "CAAU2314798"})

    assert response.status_code == 200
    body = response.json()
    assert body["status_code"] == "XF"  # events/status from ContainerHistory are unaffected
    assert len(body["details"]) == 1
    assert body["details"][0]["status_code"] == "IF"


def test_identical_lookup_is_served_from_cache_not_a_second_sapt_call(client, httpx_mock):
    _mock_full_lookup(httpx_mock)

    first = client.post("/api/tracking", json={"container_number": "CAAU2314798"})
    second = client.post("/api/tracking", json={"container_number": "caau2314798"})  # different case, same container

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    # Exactly three outbound requests were registered/consumed (one history
    # + two details) -- pytest-httpx fails the test on teardown if a
    # registered response goes unused, and fails immediately on a fourth,
    # unmatched request. Either way, this only passes if the second lookup
    # was served entirely from cache.


def test_response_never_leaks_sapt_cookies_or_headers(client, httpx_mock):
    httpx_mock.add_response(
        text=fixture_html("sapt_container_history_valid.html"),
        headers={"Set-Cookie": "ARRAffinity=deadbeef; Path=/"},
    )
    httpx_mock.add_response(text=fixture_html("sapt_container_details_xf.html"))
    httpx_mock.add_response(text=fixture_html("sapt_container_details_if.html"))

    response = client.post("/api/tracking", json={"container_number": "CAAU2314798"})

    assert response.status_code == 200
    assert "set-cookie" not in {h.lower() for h in response.headers.keys()}
