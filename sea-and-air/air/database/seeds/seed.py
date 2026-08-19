"""Idempotent demo data for the 17-stage pipeline: the Lahore-Dubai air
lane with multiple rate breaks, four customers, four inquiries carried to
different points of the workflow (a draft quote, a shipment mid-Airport-
phase, an accepted shipment marked at risk, and one carried all the way to
Invoice to Customer, which also gets a real Invoice generated from its
quote), the thirteen worker areas (one per worker-assignable stage), a demo
worker account per area, a customer portal login for the two higher-volume
demo customers, and the two real Raaziq issuing entities (Pakistan and UK).

Sea and road rate cards are not seeded -- this deployment only quotes air
freight (the TransportMode enum still supports sea/road for later, but no
lane data exists for them, so they can't be selected in practice).

Safe to run repeatedly: every entity is looked up by a natural key before
being created, so re-running never duplicates rows. Run with:

    uv run python database/seeds/seed.py
"""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

# This file lives at air/database/seeds/seed.py, outside the air/backend
# package it needs to import from -- add it to sys.path explicitly so this
# script works regardless of the caller's cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import models as m  # noqa: E402
from db import SessionLocal  # noqa: E402
from models.enums import (  # noqa: E402
    ChargeBasis,
    ChargeKind,
    EventSource,
    ShipmentStage,
    TransportMode,
    UnitOfMeasure,
    next_stage,
)
from schemas.inquiries import InquiryCreate  # noqa: E402
from utils.security import hash_password  # noqa: E402
from services.companies import list_companies  # noqa: E402
from services.customers import grant_portal_access  # noqa: E402
from services.inquiries import create_inquiry  # noqa: E402
from services.invoices import create_invoice_from_quote  # noqa: E402
from services.quotes import accept_quote, generate_quote, send_quote  # noqa: E402
from services.shipments import set_routing  # noqa: E402
from services.transitions import advance_stage, set_risk  # noqa: E402

SEED_TODAY = date(2026, 6, 1)

# Every worker seeded below shares this password. Demo-only -- see README.
DEMO_WORKER_PASSWORD = "Worker123!"

# Only the higher-volume demo customers get a portal login, matching how
# ops would actually use POST /customers/{id}/portal-access -- most
# customers never get one. Demo-only -- see README.
DEMO_CUSTOMER_PASSWORD = "Customer123!"

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
    ("Bilal Sheikh", "bilal.pickup", ShipmentStage.PICKUP),
    ("Kamran Aziz", "kamran.gatein", ShipmentStage.GATE_IN),
    ("Nadia Yousuf", "nadia.receipt", ShipmentStage.SHIPMENT_RECEIPT),
    ("Saad Hussain", "saad.weighment", ShipmentStage.WEIGHMENT),
    ("Usman Tariq", "usman.gd", ShipmentStage.GD),
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


def _seed_companies(session: Session) -> None:
    # Real Raaziq letterheads, from the two reference documents read this
    # session -- non-sensitive fields only. Bank details are seeded as
    # placeholders, never the real account numbers/IBAN read from those
    # documents.
    _get_or_create(
        session, m.Company, {"name": "Raaziq International (Pvt) Ltd"},
        {
            "address": "The Enterprise, Building 2, 4th Floor, 15-KM Multan Road, Lahore, Pakistan",
            "phone": "+92-42-37516307-20",
            "email": "info@raaziq.com",
            "website": "www.raaziq.com",
            "tax_id_label": "NTN",
            "tax_id": "DEMO-0000000",
            "company_reg_no": "DEMO-0000000",
            "bank_name": "Demo Bank Pakistan",
            "bank_account_title": "Raaziq International (Pvt) Ltd",
            "bank_account_number": "DEMO-0000000",
            "bank_sort_code": "DEMO-0000",
            "is_default": True,
        },
    )
    _get_or_create(
        session, m.Company, {"name": "Raaziq International Limited - UK"},
        {
            "address": "12 Devoke Grove, Farnworth, Bolton, United Kingdom BL4 0PU",
            "phone": "0044-7459673319",
            "email": "info@raaziq.com",
            "website": "www.raaziq.com",
            "tax_id_label": "VAT No",
            "tax_id": "DEMO000000",
            "company_reg_no": "DEMO00000",
            "bank_name": "Demo Bank UK",
            "bank_account_title": "Raaziq International Limited",
            "bank_account_number": "DEMO0000",
            "bank_sort_code": "00-00-00",
            "is_default": False,
        },
    )


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
    incoterm: str, tag: str, **extra,
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
        ready_date=SEED_TODAY, incoterm=incoterm, description=description, **extra,
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
    _seed_companies(session)
    _seed_rate_card(session)
    areas = _seed_areas(session)
    _seed_workers(session, areas)
    actor_by_stage = {stage: name for name, _, stage in WORKER_DEFINITIONS}

    bilal = _seed_customer(session, name="Bilal Textiles", company_name="Bilal Textiles (Pvt) Ltd", email="ops@bilaltextiles.pk", phone="+92-42-1110001")
    orient = _seed_customer(session, name="Orient Traders", company_name="Orient Traders Ltd", email="logistics@orienttraders.pk", phone="+92-21-1110002")
    hamid = _seed_customer(session, name="Hamid Motors", company_name="Hamid Motors Karachi", email="shipping@hamidmotors.pk", phone="+92-21-1110003")
    zainab = _seed_customer(session, name="Zainab Enterprises", company_name="Zainab Enterprises Ltd", email="trade@zainabenterprises.pk", phone="+92-42-1110004")

    # Orient Traders and Zainab Enterprises are the "significant volume"
    # clients who get a portal login -- one with an active shipment, one
    # with a completed one, so both dashboard states are demoable.
    grant_portal_access(session, orient, username="orient.traders", password=DEMO_CUSTOMER_PASSWORD)
    grant_portal_access(session, zainab, username="zainab.enterprises", password=DEMO_CUSTOMER_PASSWORD)

    inq_draft = _seed_inquiry(session, customer=bilal, cargo_type="Garments", weight_kg=Decimal("120"), volume_cbm=Decimal("0.6"), incoterm="DAP", tag="draft-quote")
    inq_mid = _seed_inquiry(session, customer=orient, cargo_type="Electronics components", weight_kg=Decimal("340"), volume_cbm=Decimal("1.8"), incoterm="FOB", tag="mid-airport")
    inq_at_risk = _seed_inquiry(session, customer=hamid, cargo_type="Auto parts", weight_kg=Decimal("610"), volume_cbm=Decimal("3.1"), incoterm="EXW", tag="accepted-at-risk")
    inq_delivered = _seed_inquiry(
        session, customer=zainab, cargo_type="Textile machinery parts", weight_kg=Decimal("890"), volume_cbm=Decimal("4.5"),
        incoterm="DAP", tag="fully-invoiced",
        hs_code="8452.90", pieces=12,
        supplier_name="Zainab Textile Machinery Works", supplier_address="Industrial Estate, Faisalabad, Pakistan",
    )

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
    # ops -- proves the complete 17-stage lifecycle end to end, and also gets
    # a real Invoice generated from its quote, so the quote-to-invoice
    # workflow is visible immediately without manual clicking.
    quote_delivered = session.execute(select(m.Quote).where(m.Quote.inquiry_id == inq_delivered.id)).scalars().first()
    if quote_delivered is None:
        quote_delivered = generate_quote(session, inq_delivered.id, today=SEED_TODAY)
        send_quote(session, quote_delivered.id, today=SEED_TODAY)
        shipment = accept_quote(session, quote_delivered.id, "seed", today=SEED_TODAY)
        set_routing(session, shipment, carrier="PIA Cargo", voyage_flight_number="PK-302")
        _walk_to(session, shipment, ShipmentStage.ARRIVAL, actor_by_stage)
        advance_stage(
            session, shipment, ShipmentStage.INVOICE_TO_CUSTOMER,
            actor="ops", note="Invoice sent to customer.", source=EventSource.MANUAL,
        )
        session.flush()

    if quote_delivered.invoice is None:
        default_company = next(c for c in list_companies(session) if c.is_default)
        create_invoice_from_quote(session, quote_delivered.id, company_id=default_company.id, today=SEED_TODAY)
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
