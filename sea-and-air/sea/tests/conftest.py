"""Shared fixtures. `client` exercises the API through FastAPI's
TestClient; `fixture_html` loads a saved real (or synthetic) SAPT response
body by name from tests/fixtures/.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.tracking import _cache
from main import app as fastapi_app

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def client():
    with TestClient(fastapi_app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _reset_tracking_cache():
    # The tracking cache is a module-level singleton (see api/tracking.py)
    # so its entries persist across requests within one process -- exactly
    # what it's for in production, but tests need a clean slate each time
    # so one test's cached result can't leak into another's assertions.
    _cache._entries.clear()
    yield
    _cache._entries.clear()


def fixture_html(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")
