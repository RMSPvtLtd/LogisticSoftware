from datetime import date

from models.enums import EventSource, ShipmentStage
from services.quotes import accept_quote, generate_quote
from services.transitions import advance_stage
from factories import make_area, make_customer, make_inquiry, make_worker, simple_rate_card

TODAY = date(2026, 6, 1)

# Steps between job_opening and customs_clearance -- used to walk a shipment
# to "waiting for Customs Clearance" without hardcoding stage positions twice.
STEPS_TO_CUSTOMS_CLEARANCE = [
    ShipmentStage.AIRWAY_BILL,
    ShipmentStage.PICKUP,
    ShipmentStage.GATE_IN,
    ShipmentStage.SHIPMENT_RECEIPT,
    ShipmentStage.WEIGHMENT,
    ShipmentStage.GD,
    ShipmentStage.CUSTOMS_EXAMINATION,
]


def _accepted_shipment(db_session, **inquiry_overrides):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer, **inquiry_overrides)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    return accept_quote(db_session, quote.id, "ops", today=TODAY)


def _login(client, username: str, password: str = "Worker123!") -> str:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_queue_shows_only_shipments_at_the_preceding_stage(client, db_session):
    airway_bill_area = make_area(db_session, ShipmentStage.AIRWAY_BILL)
    make_worker(db_session, airway_bill_area, username="ali.airwaybill")

    ready = _accepted_shipment(db_session)  # at job_opening -- ready for airway_bill
    not_ready = _accepted_shipment(db_session)
    advance_stage(db_session, not_ready, ShipmentStage.AIRWAY_BILL, actor="ops", note=None, source=EventSource.MANUAL)
    advance_stage(db_session, not_ready, ShipmentStage.PICKUP, actor="ops", note=None, source=EventSource.MANUAL)
    db_session.commit()

    token = _login(client, "ali.airwaybill")
    r = client.get("/worker/queue", headers=_auth_headers(token))
    assert r.status_code == 200, r.text
    ids = [item["id"] for item in r.json()]
    assert ready.id in ids
    assert not_ready.id not in ids


def test_queue_requires_authentication(client):
    r = client.get("/worker/queue")
    assert r.status_code == 401


def test_two_workers_in_the_same_area_see_the_same_queue(client, db_session):
    customs_area = make_area(db_session, ShipmentStage.CUSTOMS_CLEARANCE)
    make_worker(db_session, customs_area, username="omar.customs")
    make_worker(db_session, customs_area, username="sana.customs")

    shipment = _accepted_shipment(db_session)
    for stage in STEPS_TO_CUSTOMS_CLEARANCE:
        advance_stage(db_session, shipment, stage, actor="ops", note=None, source=EventSource.MANUAL)
    db_session.commit()

    token_omar = _login(client, "omar.customs")
    token_sana = _login(client, "sana.customs")

    r1 = client.get("/worker/queue", headers=_auth_headers(token_omar))
    r2 = client.get("/worker/queue", headers=_auth_headers(token_sana))
    ids1 = [item["id"] for item in r1.json()]
    ids2 = [item["id"] for item in r2.json()]
    assert shipment.id in ids1
    assert shipment.id in ids2


def test_complete_stage_succeeds_when_shipment_is_ready(client, db_session):
    airway_bill_area = make_area(db_session, ShipmentStage.AIRWAY_BILL)
    make_worker(db_session, airway_bill_area, name="Ayesha Raza", username="ayesha.airwaybill")

    shipment = _accepted_shipment(db_session)
    db_session.commit()
    shipment_id = shipment.id

    token = _login(client, "ayesha.airwaybill")
    r = client.post(
        f"/worker/shipments/{shipment_id}/complete",
        json={"note": "Airway bill filed and verified"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text

    check = client.get(f"/shipments/{shipment_id}")
    assert check.json()["stage"] == "airway_bill"
    last_event = check.json()["status_events"][-1]
    assert last_event["actor"] == "Ayesha Raza"
    assert last_event["source"] == "manual"
    assert last_event["note"] == "Airway bill filed and verified"


def test_complete_stage_rejected_when_shipment_not_ready(client, db_session):
    # Worker is in Customs Clearance, but the shipment is still at
    # job_opening -- seven stages away.
    customs_area = make_area(db_session, ShipmentStage.CUSTOMS_CLEARANCE)
    make_worker(db_session, customs_area, username="omar.customs")

    shipment = _accepted_shipment(db_session)
    db_session.commit()
    shipment_id = shipment.id

    token = _login(client, "omar.customs")
    r = client.post(f"/worker/shipments/{shipment_id}/complete", json={}, headers=_auth_headers(token))
    assert r.status_code == 409

    check = client.get(f"/shipments/{shipment_id}")
    assert check.json()["stage"] == "job_opening", "shipment must not have been mutated"


def test_complete_stage_requires_authentication(client, db_session):
    shipment = _accepted_shipment(db_session)
    db_session.commit()

    r = client.post(f"/worker/shipments/{shipment.id}/complete", json={})
    assert r.status_code == 401


def test_inactive_worker_cannot_use_existing_token_flows(client, db_session):
    airway_bill_area = make_area(db_session, ShipmentStage.AIRWAY_BILL)
    make_worker(db_session, airway_bill_area, username="ali.airwaybill", is_active=False)
    db_session.commit()

    r = client.post("/auth/login", json={"username": "ali.airwaybill", "password": "Worker123!"})
    assert r.status_code == 401
