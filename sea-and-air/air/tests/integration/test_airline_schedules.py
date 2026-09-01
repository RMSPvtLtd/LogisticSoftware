VALID_PAYLOAD = {
    "airline_name": "PIA",
    "origin": "Lahore",
    "destination": "London",
    "mode": "air",
    "days_of_week": ["mon", "wed", "fri"],
    "notes": "Cargo hold only, no belly space on Sundays",
}


def test_create_airline_schedule(client, ops_headers):
    r = client.post("/airline-schedules", json=VALID_PAYLOAD, headers=ops_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["airline_name"] == "PIA"
    assert body["days_of_week"] == ["mon", "wed", "fri"]


def test_create_airline_schedule_requires_ops_auth(client):
    r = client.post("/airline-schedules", json=VALID_PAYLOAD)
    assert r.status_code == 401


def test_create_airline_schedule_rejects_empty_days(client, ops_headers):
    payload = {**VALID_PAYLOAD, "days_of_week": []}
    r = client.post("/airline-schedules", json=payload, headers=ops_headers)
    assert r.status_code == 422


def test_create_airline_schedule_rejects_invalid_day_name(client, ops_headers):
    payload = {**VALID_PAYLOAD, "days_of_week": ["mon", "someday"]}
    r = client.post("/airline-schedules", json=payload, headers=ops_headers)
    assert r.status_code == 422


def test_list_and_get_airline_schedule(client, ops_headers):
    created = client.post("/airline-schedules", json=VALID_PAYLOAD, headers=ops_headers).json()

    listed = client.get("/airline-schedules", headers=ops_headers)
    assert listed.status_code == 200
    assert any(s["id"] == created["id"] for s in listed.json())

    fetched = client.get(f"/airline-schedules/{created['id']}", headers=ops_headers)
    assert fetched.status_code == 200
    assert fetched.json()["days_of_week"] == ["mon", "wed", "fri"]


def test_get_airline_schedule_not_found(client, ops_headers):
    r = client.get("/airline-schedules/999999", headers=ops_headers)
    assert r.status_code == 404


def test_update_airline_schedule(client, ops_headers):
    created = client.post("/airline-schedules", json=VALID_PAYLOAD, headers=ops_headers).json()

    updated_payload = {**VALID_PAYLOAD, "days_of_week": ["tue", "thu"], "notes": None}
    r = client.patch(f"/airline-schedules/{created['id']}", json=updated_payload, headers=ops_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["days_of_week"] == ["tue", "thu"]
    assert body["notes"] is None


def test_delete_airline_schedule(client, ops_headers):
    created = client.post("/airline-schedules", json=VALID_PAYLOAD, headers=ops_headers).json()

    r = client.delete(f"/airline-schedules/{created['id']}", headers=ops_headers)
    assert r.status_code == 204

    r = client.get(f"/airline-schedules/{created['id']}", headers=ops_headers)
    assert r.status_code == 404
