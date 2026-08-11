"""Idempotent demo data for the 17-stage pipeline: the Lahore-Dubai air
lane with multiple rate breaks, four customers, four inquiries carried to
different points of the workflow (a draft quote, a shipment mid-Airport-
phase, an accepted shipment marked at risk, and one carried all the way to
Invoice to Customer), the thirteen worker areas (one per worker-assignable
stage), and a demo worker account per area.

Sea and road rate cards are not seeded -- this deployment only quotes air
freight (the TransportMode enum still supports sea/road for later, but no
lane data exists for them, so they can't be selected in practice).

Safe to run repeatedly: every entity is looked up by a natural key before
being created, so re-running never duplicates rows. Run with:

    uv run python -m seeds.seed
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models as m
from app.db import SessionLocal
from app.models.enums import ChargeBasis, ChargeKind, EventSource, ShipmentStage, TransportMode, UnitOfMeasure, next_stage
from app.schemas.inquiries import InquiryCreate
from app.security import hash_password
from app.services.inquiries import create_inquiry
from app.services.quotes import accept_quote, generate_quote, send_quote
from app.services.transitions import advance_stage, set_risk

SEED_TODAY = date(2026, 6, 1)

# Every worker seeded below shares this password. Demo-only -- see README.
DEMO_WORKER_PASSWORD = "Worker123!"

# One area per worker-assignable stage, in pipeline order. A second worker
# is seeded for Customs Clearance to demonstrate that an area's queue is
# shared by anyone in it, not owned by one fixed person.
AREA_DEFINITIONS: list[tuple[str, ShipmentStage]] = [
    ("Airway Bill", ShipmentStage.AIRWAY_BILL),
    ("GD", ShipmentStage.GD),
    ("Pickup", ShipmentStage.PICKUP),
    ("Gate In", ShipmentStage.GATE_IN),
    ("Shipment Receipt", ShipmentStage.SHIPMENT_RECEIPT),
    ("Weighment", ShipmentStage.WEIGHMENT),
    ("Customs Examination", ShipmentStage.CUSTOMS_EXAMINATION),
    ("Customs Clearance", ShipmentStage.CUSTOMS_CLEARANCE),
    ("Scanning", ShipmentStage.SCANNING),
    ("Handover", ShipmentStage.HANDOVER),
    ("Departure", ShipmentStage.DEPARTURE),
    ("Transhipment", ShipmentStage.TRANSHIPMENT),
    ("Arrival", ShipmentStage.ARRIVAL),
]

WORKER_DEFINITIONS: list[tuple[str, str, ShipmentStage]] = [
    ("Ayesha Raza", "ayesha.airwaybill", ShipmentStage.AIRWAY_BILL),
    ("Usman Tariq", "usman.gd", ShipmentStage.GD),
    ("Bilal Sheikh", "bilal.pickup", ShipmentStage.PICKUP),
    ("Kamran Aziz", "kamran.gatein", ShipmentStage.GATE_IN),
    ("Nadia Yousuf", "nadia.receipt", ShipmentStage.SHIPMENT_RECEIPT),
    ("Saad Hussain", "saad.weighment", ShipmentStage.WEIGHMENT),
    ("Fatima Noor", "fatima.examination", ShipmentStage.CUSTOMS_EXAMINATION),
    ("Omar Farooq", "omar.customs", ShipmentStage.CUSTOMS_CLEARANCE),
    ("Sana Malik", "sana.customs", ShipmentStage.CUSTOMS_CLEARANCE),
    ("Hamza Iqbal", "hamza.scanning", ShipmentStage.SCANNING),
    ("Rabia Siddiqui", "rabia.handover", ShipmentStage.HANDOVER),
    ("Zara Iqbal", "zara.departure", ShipmentStage.DEPARTURE),
    ("Adeel Khan", "adeel.transhipment", ShipmentStage.TRANSHIPMENT),
    ("Hina Chaudhry", "hina.arrival", ShipmentStage.ARRIVAL),
]


def _get_or_create(session: Session, model, lookup: dict, defaults: dict | None = None):
    instance = session.execute(select(model).filter_by(**lookup)).scalars().first()
    if instance is not None:
        return instance, False
    instance = model(**lookup, **(defaults or {}))
    session.add(instance)
    session.flush()
    return instance, True


def _seed_customer(session: Session, *, name: str, company_name: str, email: str, phone: str) -> m.Customer:
    customer, _ = _get_or_create(
        session, m.Customer, {"email": email}, {"name": name, "company_name": company_name, "phone": phone}
    )
    return customer


def _seed_rate_card(session: Session) -> m.RateCard:
    rate_card, created = _get_or_create(
        session,
        m.RateCard,
        {"origin": "Lahore", "destination": "Dubai", "mode": TransportMode.AIR, "carrier": "PIA Cargo"},
        {
            "currency": "USD",
            "valid_from": date(2020, 1, 1),
            "valid_until": date(2035, 1, 1),
            "minimum_charge": Decimal("60"),
        },
    )
    if created:
        session.add_all(
            [
                m.RateCardBreak(rate_card_id=rate_card.id, min_weight=Decimal("0"), max_weight=Decimal("100"), unit=UnitOfMeasure.PER_KG, rate=Decimal("6.50"), description="0-100kg"),
                m.RateCardBreak(rate_card_id=rate_card.id, min_weight=Decimal("100"), max_weight=Decimal("500"), unit=UnitOfMeasure.PER_KG, rate=Decimal("5.20"), description="100-500kg"),
                m.RateCardBreak(rate_card_id=rate_card.id, min_weight=Decimal("500"), max_weight=None, unit=UnitOfMeasure.PER_KG, rate=Decimal("4.10"), description="500kg+"),
            ]
        )
        session.add_all(
            [
                m.RateCardCharge(rate_card_id=rate_card.id, kind=ChargeKind.DOCUMENTATION, description="Documentation fee", basis=ChargeBasis.FLAT, amount=Decimal("45")),
                m.RateCardCharge(rate_card_id=rate_card.id, kind=ChargeKind.PICKUP, description="Origin pickup", basis=ChargeBasis.FLAT, amount=Decimal("80")),
                m.RateCardCharge(
                    rate_card_id=rate_card.id, kind=ChargeKind.CUSTOMS, description="Customs clearance (5% of freight)",
                    basis=ChargeBasis.PERCENT_OF_FREIGHT, amount=Decimal("5.00"),
                ),
            ]
        )
        session.flush()
    return rate_card


def _seed_inquiry(
    session: Session, *, customer: m.Customer, cargo_type: str, weight_kg: Decimal, volume_cbm: Decimal,
    incoterm: str, tag: str,
) -> m.Inquiry:
    # Inquiries have no natural unique key of their own, so the seed tags each
    # one's description to make re-running the script idempotent. Creating an
    # inquiry also creates its Shipment tracking row (services.inquiries).
    description = f"[seed:{tag}] {cargo_type} shipment"
    existing = session.execute(select(m.Inquiry).where(m.Inquiry.description == description)).scalars().first()
    if existing is not None:
        return existing

    payload = InquiryCreate(
        customer_id=customer.id, origin="Lahore", destination="Dubai", mode=TransportMode.AIR,
        cargo_type=cargo_type, weight_kg=weight_kg, volume_cbm=volume_cbm,
        ready_date=SEED_TODAY, incoterm=incoterm, description=description,
    )
    return create_inquiry(session, payload)


def _seed_areas(session: Session) -> dict[ShipmentStage, m.Area]:
    areas: dict[ShipmentStage, m.Area] = {}
    for name, stage in AREA_DEFINITIONS:
        area, _ = _get_or_create(session, m.Area, {"stage": stage}, {"name": name})
        areas[stage] = area
    return areas


def _seed_workers(session: Session, areas: dict[ShipmentStage, m.Area]) -> None:
    for name, username, stage in WORKER_DEFINITIONS:
        _get_or_create(
            session, m.Worker, {"username": username},
            {"name": name, "password_hash": hash_password(DEMO_WORKER_PASSWORD), "area_id": areas[stage].id},
        )


def _walk_to(session: Session, shipment: m.Shipment, target: ShipmentStage, actors: dict[ShipmentStage, str]) -> None:
    """Advance a shipment stage by stage up to (and including) `target`,
    using the demo worker responsible for each stage as the actor -- exactly
    what happens when each worker marks their own queue item done.
    """
    while shipment.stage != target:
        nxt = next_stage(shipment.stage)
        advance_stage(
            session, shipment, nxt,
            actor=actors.get(nxt, "ops"), note=f"{nxt.value.replace('_', ' ').title()} completed", source=EventSource.MANUAL,
        )


def run(session: Session) -> None:
    _seed_rate_card(session)
    areas = _seed_areas(session)
    _seed_workers(session, areas)
    actor_by_stage = {stage: name for name, _, stage in WORKER_DEFINITIONS}

    bilal = _seed_customer(session, name="Bilal Textiles", company_name="Bilal Textiles (Pvt) Ltd", email="ops@bilaltextiles.pk", phone="+92-42-1110001")
    orient = _seed_customer(session, name="Orient Traders", company_name="Orient Traders Ltd", email="logistics@orienttraders.pk", phone="+92-21-1110002")
    hamid = _seed_customer(session, name="Hamid Motors", company_name="Hamid Motors Karachi", email="shipping@hamidmotors.pk", phone="+92-21-1110003")
    zainab = _seed_customer(session, name="Zainab Enterprises", company_name="Zainab Enterprises Ltd", email="trade@zainabenterprises.pk", phone="+92-42-1110004")

    inq_draft = _seed_inquiry(session, customer=bilal, cargo_type="Garments", weight_kg=Decimal("120"), volume_cbm=Decimal("0.6"), incoterm="DAP", tag="draft-quote")
    inq_mid = _seed_inquiry(session, customer=orient, cargo_type="Electronics components", weight_kg=Decimal("340"), volume_cbm=Decimal("1.8"), incoterm="FOB", tag="mid-airport")
    inq_at_risk = _seed_inquiry(session, customer=hamid, cargo_type="Auto parts", weight_kg=Decimal("610"), volume_cbm=Decimal("3.1"), incoterm="EXW", tag="accepted-at-risk")
    inq_delivered = _seed_inquiry(session, customer=zainab, cargo_type="Textile machinery parts", weight_kg=Decimal("890"), volume_cbm=Decimal("4.5"), incoterm="DAP", tag="fully-invoiced")

    # Inquiry 1: quote generated, left in draft.
    if not session.execute(select(m.Quote).where(m.Quote.inquiry_id == inq_draft.id)).scalars().first():
        generate_quote(session, inq_draft.id, today=SEED_TODAY)
        session.flush()

    # Inquiry 2: accepted, walked through Documentation/Pickup and partway
    # through Airport -- currently sitting at Customs Examination.
    quote_mid = session.execute(select(m.Quote).where(m.Quote.inquiry_id == inq_mid.id)).scalars().first()
    if quote_mid is None:
        quote_mid = generate_quote(session, inq_mid.id, today=SEED_TODAY)
        send_quote(session, quote_mid.id, today=SEED_TODAY)
        shipment = accept_quote(session, quote_mid.id, "seed", today=SEED_TODAY)
        _walk_to(session, shipment, ShipmentStage.CUSTOMS_EXAMINATION, actor_by_stage)
        session.flush()

    # Inquiry 3: accepted, still at Job Opening, marked at risk.
    quote_at_risk = session.execute(select(m.Quote).where(m.Quote.inquiry_id == inq_at_risk.id)).scalars().first()
    if quote_at_risk is None:
        quote_at_risk = generate_quote(session, inq_at_risk.id, today=SEED_TODAY)
        send_quote(session, quote_at_risk.id, today=SEED_TODAY)
        shipment = accept_quote(session, quote_at_risk.id, "seed", today=SEED_TODAY)
        set_risk(session, shipment, is_at_risk=True, risk_reason="Awaiting updated commercial invoice from shipper", actor="seed")
        session.flush()

    # Inquiry 4: accepted and walked all the way through, then invoiced by
    # ops -- proves the complete 17-stage lifecycle end to end.
    quote_delivered = session.execute(select(m.Quote).where(m.Quote.inquiry_id == inq_delivered.id)).scalars().first()
    if quote_delivered is None:
        quote_delivered = generate_quote(session, inq_delivered.id, today=SEED_TODAY)
        send_quote(session, quote_delivered.id, today=SEED_TODAY)
        shipment = accept_quote(session, quote_delivered.id, "seed", today=SEED_TODAY)
        _walk_to(session, shipment, ShipmentStage.ARRIVAL, actor_by_stage)
        advance_stage(
            session, shipment, ShipmentStage.INVOICE_TO_CUSTOMER,
            actor="ops", note="Invoice sent to customer.", source=EventSource.MANUAL,
        )
        session.flush()


def main() -> None:
    session = SessionLocal()
    try:
        run(session)
        session.commit()
        print("Seed complete.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
