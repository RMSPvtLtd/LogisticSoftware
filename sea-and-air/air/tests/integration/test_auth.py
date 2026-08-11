import pytest

from utils.errors import Unauthorized
from models.enums import ShipmentStage
from services.workers import authenticate_worker
from factories import make_area, make_worker


def test_authenticate_worker_success(db_session):
    area = make_area(db_session, ShipmentStage.AIRWAY_BILL)
    worker = make_worker(db_session, area, username="ali.docs", password="Correct123!")

    authenticated = authenticate_worker(db_session, "ali.docs", "Correct123!")
    assert authenticated.id == worker.id


def test_authenticate_worker_wrong_password(db_session):
    area = make_area(db_session, ShipmentStage.AIRWAY_BILL)
    make_worker(db_session, area, username="ali.docs", password="Correct123!")

    with pytest.raises(Unauthorized):
        authenticate_worker(db_session, "ali.docs", "WrongPassword")


def test_authenticate_worker_unknown_username(db_session):
    with pytest.raises(Unauthorized):
        authenticate_worker(db_session, "nobody", "whatever")


def test_authenticate_inactive_worker_rejected(db_session):
    area = make_area(db_session, ShipmentStage.AIRWAY_BILL)
    make_worker(db_session, area, username="ali.docs", password="Correct123!", is_active=False)

    with pytest.raises(Unauthorized):
        authenticate_worker(db_session, "ali.docs", "Correct123!")


# --- HTTP layer ---


def test_login_endpoint_returns_token_and_worker(client, db_session):
    area = make_area(db_session, ShipmentStage.CUSTOMS_CLEARANCE, name="Customs")
    make_worker(db_session, area, name="Sana Malik", username="sana.customs", password="Correct123!")
    db_session.commit()

    r = client.post("/auth/login", json={"username": "sana.customs", "password": "Correct123!"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["worker"]["username"] == "sana.customs"
    assert body["worker"]["area"]["name"] == "Customs"
    assert "password" not in body["worker"]
    assert "password_hash" not in body["worker"]


def test_login_wrong_password_returns_401(client, db_session):
    area = make_area(db_session, ShipmentStage.AIRWAY_BILL)
    make_worker(db_session, area, username="ali.docs", password="Correct123!")
    db_session.commit()

    r = client.post("/auth/login", json={"username": "ali.docs", "password": "nope"})
    assert r.status_code == 401


def test_me_requires_valid_token(client, db_session):
    area = make_area(db_session, ShipmentStage.AIRWAY_BILL)
    make_worker(db_session, area, username="ali.docs", password="Correct123!")
    db_session.commit()

    r = client.get("/auth/me")
    assert r.status_code == 401

    r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401

    login = client.post("/auth/login", json={"username": "ali.docs", "password": "Correct123!"})
    token = login.json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "ali.docs"
