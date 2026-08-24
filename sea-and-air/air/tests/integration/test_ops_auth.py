from services.ops_users import authenticate_ops_user, change_ops_password
from utils.errors import InvalidPasswordChange, Unauthorized
from factories import make_ops_user

import pytest


def test_authenticate_ops_user_succeeds_with_correct_password(db_session):
    make_ops_user(db_session, username="ops.one", password="Correct123!")
    ops_user = authenticate_ops_user(db_session, "ops.one", "Correct123!")
    assert ops_user.username == "ops.one"


def test_authenticate_ops_user_rejects_wrong_password(db_session):
    make_ops_user(db_session, username="ops.two", password="Correct123!")
    with pytest.raises(Unauthorized):
        authenticate_ops_user(db_session, "ops.two", "WrongPassword!")


def test_authenticate_ops_user_rejects_deactivated_account(db_session):
    ops_user = make_ops_user(db_session, username="ops.three", password="Correct123!")
    ops_user.is_active = False
    db_session.flush()
    with pytest.raises(Unauthorized):
        authenticate_ops_user(db_session, "ops.three", "Correct123!")


def test_change_password_requires_correct_current_password(db_session):
    ops_user = make_ops_user(db_session, password="Correct123!")
    with pytest.raises(Unauthorized):
        change_ops_password(
            db_session, ops_user,
            current_password="WrongOne!", new_password="NewPassword1!", confirm_new_password="NewPassword1!",
        )


def test_change_password_requires_matching_confirmation(db_session):
    ops_user = make_ops_user(db_session, password="Correct123!")
    with pytest.raises(InvalidPasswordChange):
        change_ops_password(
            db_session, ops_user,
            current_password="Correct123!", new_password="NewPassword1!", confirm_new_password="Different1!",
        )


def test_change_password_bumps_token_version(db_session):
    ops_user = make_ops_user(db_session, password="Correct123!")
    original_version = ops_user.token_version

    change_ops_password(
        db_session, ops_user,
        current_password="Correct123!", new_password="NewPassword1!", confirm_new_password="NewPassword1!",
    )

    assert ops_user.token_version == original_version + 1
    # Old password no longer works, new one does.
    with pytest.raises(Unauthorized):
        authenticate_ops_user(db_session, ops_user.username, "Correct123!")
    assert authenticate_ops_user(db_session, ops_user.username, "NewPassword1!").id == ops_user.id


# --- API-level ---


def test_login_endpoint_issues_a_working_token(client, db_session):
    make_ops_user(db_session, username="api.ops", password="Correct123!")
    db_session.commit()

    r = client.post("/ops/login", json={"username": "api.ops", "password": "Correct123!"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    assert "password_hash" not in r.json()["ops_user"]

    r = client.get("/ops/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["username"] == "api.ops"
    assert "password_hash" not in r.json()


def test_login_endpoint_rejects_wrong_password(client, db_session):
    make_ops_user(db_session, username="api.ops2", password="Correct123!")
    db_session.commit()

    r = client.post("/ops/login", json={"username": "api.ops2", "password": "wrong"})
    assert r.status_code == 401


def test_protected_ops_route_requires_a_token(client):
    r = client.get("/shipments")
    assert r.status_code == 401


def test_protected_ops_route_rejects_a_worker_token(client, db_session):
    from factories import make_area, make_worker
    from models.enums import ShipmentStage

    area = make_area(db_session, ShipmentStage.AIRWAY_BILL)
    make_worker(db_session, area, username="a.worker", password="Correct123!")
    db_session.commit()

    login = client.post("/auth/login", json={"username": "a.worker", "password": "Correct123!"})
    token = login.json()["access_token"]

    r = client.get("/shipments", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_change_password_endpoint_revokes_old_tokens(client, db_session):
    make_ops_user(db_session, username="api.ops3", password="Correct123!")
    db_session.commit()

    old_token = client.post(
        "/ops/login", json={"username": "api.ops3", "password": "Correct123!"}
    ).json()["access_token"]

    r = client.post(
        "/ops/change-password",
        json={"current_password": "Correct123!", "new_password": "NewPassword1!", "confirm_new_password": "NewPassword1!"},
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert r.status_code == 200, r.text

    # The token issued before the change no longer works anywhere.
    r = client.get("/shipments", headers={"Authorization": f"Bearer {old_token}"})
    assert r.status_code == 401

    # The old password no longer logs in; the new one does.
    r = client.post("/ops/login", json={"username": "api.ops3", "password": "Correct123!"})
    assert r.status_code == 401
    r = client.post("/ops/login", json={"username": "api.ops3", "password": "NewPassword1!"})
    assert r.status_code == 200


def test_change_password_endpoint_requires_authentication(client, db_session):
    make_ops_user(db_session, username="api.ops4", password="Correct123!")
    db_session.commit()

    r = client.post(
        "/ops/change-password",
        json={"current_password": "Correct123!", "new_password": "NewPassword1!", "confirm_new_password": "NewPassword1!"},
    )
    assert r.status_code == 401


def test_change_password_endpoint_rejects_mismatched_confirmation(client, db_session, ops_headers):
    r = client.post(
        "/ops/change-password",
        json={"current_password": "OpsTest123!", "new_password": "NewPassword1!", "confirm_new_password": "Different1!"},
        headers=ops_headers,
    )
    assert r.status_code == 422
