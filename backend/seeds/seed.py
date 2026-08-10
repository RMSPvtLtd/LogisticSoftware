"""Idempotent demo data: the Lahore-Dubai air lane with multiple rate
breaks, three customers, three inquiries carried to different points of the
workflow (draft quote, accepted + in transit, accepted + at risk), the six
worker areas (one per operational stage after job_opened), and a demo
worker account per area, so the whole demo flow in the README can be walked
without creating anything by hand first.

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
from app.models.enums import ChargeBasis, ChargeKind, EventSource, ShipmentStage, TransportMode, UnitOfMeasure
from app.security import hash_password
from app.services.quotes import accept_quote, generate_quote, send_quote
from app.services.transitions import advance_stage, set_risk

SEED_TODAY = date(2026, 6, 1)

# Every worker seeded below shares this password. Demo-only -- see README.
DEMO_WORKER_PASSWORD = "Worker123!"


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


def _seed_rate_card(
    session: Session,
    *,
    origin: str,
    destination: str,
    mode: TransportMode,
    carrier: str,
    currency: str,
    minimum_charge: Decimal,
    breaks: list[dict],
    charges: list[dict],
) -> m.RateCard:
    rate_card, created = _get_or_create(
        session,
        m.RateCard,
        {"origin": origin, "destination": destination, "mode": mode, "carrier": carrier},
        {
            "currency": currency,
            "valid_from": date(2020, 1, 1),
            "valid_until": date(2035, 1, 1),
            "minimum_charge": minimum_charge,
        },
    )
    if created:
        for b in breaks:
            session.add(m.RateCardBreak(rate_card_id=rate_card.id, **b))
        for c in charges:
            session.add(m.RateCardCharge(rate_card_id=rate_card.id, **c))
        session.flush()
    return rate_card


def _seed_inquiry(
    session: Session,
    *,
    customer: m.Customer,
    origin: str,
    destination: str,
    mode: TransportMode,
    cargo_type: str,
    weight_kg: Decimal,
    volume_cbm: Decimal,
    incoterm: str,
    tag: str,
) -> m.Inquiry:
    # Inquiries have no natural unique key of their own, so the seed tags each
    # one's description to make re-running the script idempotent.
    description = f"[seed:{tag}] {cargo_type} shipment"
    inquiry = session.execute(select(m.Inquiry).where(m.Inquiry.description == description)).scalars().first()
    if inquiry is not None:
        return inquiry
    inquiry = m.Inquiry(
        customer_id=customer.id,
        origin=origin,
        destination=destination,
        mode=mode,
        cargo_type=cargo_type,
        weight_kg=weight_kg,
        volume_cbm=volume_cbm,
        ready_date=SEED_TODAY,
        incoterm=incoterm,
        description=description,
    )
    session.add(inquiry)
    session.flush()
    return inquiry


def _seed_lane(session: Session) -> None:
    _seed_rate_card(
        session,
        origin="Lahore",
        destination="Dubai",
        mode=TransportMode.AIR,
        carrier="PIA Cargo",
        currency="USD",
        minimum_charge=Decimal("60"),
        breaks=[
            dict(min_weight=Decimal("0"), max_weight=Decimal("100"), unit=UnitOfMeasure.PER_KG, rate=Decimal("6.50"), description="0-100kg"),
            dict(min_weight=Decimal("100"), max_weight=Decimal("500"), unit=UnitOfMeasure.PER_KG, rate=Decimal("5.20"), description="100-500kg"),
            dict(min_weight=Decimal("500"), max_weight=None, unit=UnitOfMeasure.PER_KG, rate=Decimal("4.10"), description="500kg+"),
        ],
        charges=[
            dict(kind=ChargeKind.DOCUMENTATION, description="Documentation fee", basis=ChargeBasis.FLAT, amount=Decimal("45")),
            dict(kind=ChargeKind.PICKUP, description="Origin pickup", basis=ChargeBasis.FLAT, amount=Decimal("80")),
            dict(
                kind=ChargeKind.CUSTOMS,
                description="Customs clearance (5% of freight)",
                basis=ChargeBasis.PERCENT_OF_FREIGHT,
                amount=Decimal("5.00"),
            ),
        ],
    )


def _seed_areas(session: Session) -> dict[ShipmentStage, m.Area]:
    definitions = [
        ("Documentation", ShipmentStage.DOCS_FILED),
        ("Pickup", ShipmentStage.PICKED_UP),
        ("Transit", ShipmentStage.IN_TRANSIT),
        ("Customs", ShipmentStage.CUSTOMS_CLEARANCE),
        ("Arrival", ShipmentStage.ARRIVED),
        ("Delivery", ShipmentStage.DELIVERED),
    ]
    areas: dict[ShipmentStage, m.Area] = {}
    for name, stage in definitions:
        area, _ = _get_or_create(session, m.Area, {"stage": stage}, {"name": name})
        areas[stage] = area
    return areas


def _seed_worker(session: Session, *, name: str, username: str, area: m.Area) -> None:
    _get_or_create(
        session,
        m.Worker,
        {"username": username},
        {"name": name, "password_hash": hash_password(DEMO_WORKER_PASSWORD), "area_id": area.id},
    )


def _seed_workers(session: Session, areas: dict[ShipmentStage, m.Area]) -> None:
    _seed_worker(session, name="Ayesha Raza", username="ayesha.docs", area=areas[ShipmentStage.DOCS_FILED])
    _seed_worker(session, name="Bilal Sheikh", username="bilal.pickup", area=areas[ShipmentStage.PICKED_UP])
    _seed_worker(session, name="Zara Iqbal", username="zara.transit", area=areas[ShipmentStage.IN_TRANSIT])
    _seed_worker(session, name="Omar Farooq", username="omar.customs", area=areas[ShipmentStage.CUSTOMS_CLEARANCE])
    # A second Customs worker to demonstrate that any worker in an area
    # shares the same queue -- not a one-worker-per-stage restriction.
    _seed_worker(session, name="Sana Malik", username="sana.customs", area=areas[ShipmentStage.CUSTOMS_CLEARANCE])
    _seed_worker(session, name="Hina Chaudhry", username="hina.arrival", area=areas[ShipmentStage.ARRIVED])
    _seed_worker(session, name="Faisal Ahmed", username="faisal.delivery", area=areas[ShipmentStage.DELIVERED])


def run(session: Session) -> None:
    _seed_lane(session)
    areas = _seed_areas(session)
    _seed_workers(session, areas)

    bilal = _seed_customer(
        session, name="Bilal Textiles", company_name="Bilal Textiles (Pvt) Ltd",
        email="ops@bilaltextiles.pk", phone="+92-42-1110001",
    )
    orient = _seed_customer(
        session, name="Orient Traders", company_name="Orient Traders Ltd",
        email="logistics@orienttraders.pk", phone="+92-21-1110002",
    )
    hamid = _seed_customer(
        session, name="Hamid Motors", company_name="Hamid Motors Karachi",
        email="shipping@hamidmotors.pk", phone="+92-21-1110003",
    )

    inq_draft = _seed_inquiry(
        session, customer=bilal, origin="Lahore", destination="Dubai", mode=TransportMode.AIR,
        cargo_type="Garments", weight_kg=Decimal("120"), volume_cbm=Decimal("0.6"),
        incoterm="DAP", tag="draft-quote",
    )
    inq_in_transit = _seed_inquiry(
        session, customer=orient, origin="Lahore", destination="Dubai", mode=TransportMode.AIR,
        cargo_type="Electronics components", weight_kg=Decimal("340"), volume_cbm=Decimal("1.8"),
        incoterm="FOB", tag="accepted-in-transit",
    )
    inq_at_risk = _seed_inquiry(
        session, customer=hamid, origin="Lahore", destination="Dubai", mode=TransportMode.AIR,
        cargo_type="Auto parts", weight_kg=Decimal("610"), volume_cbm=Decimal("3.1"),
        incoterm="EXW", tag="accepted-at-risk",
    )

    # Quote 1: left in draft so the UI has something to demo overriding/sending.
    if not session.execute(select(m.Quote).where(m.Quote.inquiry_id == inq_draft.id)).scalars().first():
        generate_quote(session, inq_draft.id, today=SEED_TODAY)
        session.flush()

    # Quote 2: accepted, shipment progressed through in_transit.
    quote_in_transit = session.execute(
        select(m.Quote).where(m.Quote.inquiry_id == inq_in_transit.id)
    ).scalars().first()
    if quote_in_transit is None:
        quote_in_transit = generate_quote(session, inq_in_transit.id, today=SEED_TODAY)
        send_quote(session, quote_in_transit.id, today=SEED_TODAY)
        shipment = accept_quote(session, quote_in_transit.id, "seed", today=SEED_TODAY)
        advance_stage(
            session, shipment, ShipmentStage.DOCS_FILED,
            actor="seed", note="Export documentation filed", source=EventSource.MANUAL,
        )
        advance_stage(
            session, shipment, ShipmentStage.PICKED_UP,
            actor="seed", note="Cargo picked up from Lahore warehouse", source=EventSource.MANUAL,
        )
        advance_stage(
            session, shipment, ShipmentStage.IN_TRANSIT,
            actor="seed", note="Flight departed Lahore", source=EventSource.MANUAL,
        )
        session.flush()

    # Quote 3: accepted, shipment at job_opened and marked at risk.
    quote_at_risk = session.execute(
        select(m.Quote).where(m.Quote.inquiry_id == inq_at_risk.id)
    ).scalars().first()
    if quote_at_risk is None:
        quote_at_risk = generate_quote(session, inq_at_risk.id, today=SEED_TODAY)
        send_quote(session, quote_at_risk.id, today=SEED_TODAY)
        shipment = accept_quote(session, quote_at_risk.id, "seed", today=SEED_TODAY)
        set_risk(
            session, shipment, is_at_risk=True,
            risk_reason="Awaiting updated commercial invoice from shipper", actor="seed",
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
