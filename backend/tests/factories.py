"""Small object-creation helpers shared across tests. Not fixtures
themselves (fixtures own the session) — plain functions the tests call with
whatever session fixture they're using.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models as m
from app.models.enums import ChargeBasis, ShipmentStage, TransportMode, UnitOfMeasure
from app.schemas.inquiries import InquiryCreate
from app.security import hash_password
from app.services.inquiries import create_inquiry


def make_customer(session: Session, **overrides) -> m.Customer:
    defaults = dict(
        name="Test Shipper",
        company_name="Test Shipper Ltd",
        email=f"test-{uuid.uuid4().hex[:10]}@example.com",
        phone="+92-300-0000000",
    )
    defaults.update(overrides)
    customer = m.Customer(**defaults)
    session.add(customer)
    session.flush()
    return customer


def make_customer_with_portal(
    session: Session, *, password: str = "Customer123!", **overrides
) -> m.Customer:
    overrides.setdefault("username", f"customer-{uuid.uuid4().hex[:10]}")
    overrides["password_hash"] = hash_password(password)
    overrides["portal_active"] = True
    return make_customer(session, **overrides)


def make_rate_card(
    session: Session,
    *,
    origin: str = "Lahore",
    destination: str = "Dubai",
    mode: TransportMode = TransportMode.AIR,
    carrier: str = "TestAir",
    currency: str = "USD",
    valid_from: date = date(2020, 1, 1),
    valid_until: date = date(2035, 1, 1),
    minimum_charge: Decimal = Decimal("50"),
) -> m.RateCard:
    rate_card = m.RateCard(
        origin=origin,
        destination=destination,
        mode=mode,
        carrier=carrier,
        currency=currency,
        valid_from=valid_from,
        valid_until=valid_until,
        minimum_charge=minimum_charge,
    )
    session.add(rate_card)
    session.flush()
    return rate_card


def add_break(session: Session, rate_card: m.RateCard, **kwargs) -> m.RateCardBreak:
    kwargs.setdefault("unit", UnitOfMeasure.PER_KG)
    brk = m.RateCardBreak(rate_card_id=rate_card.id, **kwargs)
    session.add(brk)
    session.flush()
    return brk


def add_charge(session: Session, rate_card: m.RateCard, **kwargs) -> m.RateCardCharge:
    kwargs.setdefault("basis", ChargeBasis.FLAT)
    charge = m.RateCardCharge(rate_card_id=rate_card.id, **kwargs)
    session.add(charge)
    session.flush()
    return charge


def make_inquiry(session: Session, customer: m.Customer, **overrides) -> m.Inquiry:
    """Goes through the real create_inquiry service (not a raw insert) so
    the Shipment tracking row that must exist alongside every Inquiry is
    always created too — the same thing the API does.
    """
    defaults = dict(
        origin="Lahore",
        destination="Dubai",
        mode=TransportMode.AIR,
        cargo_type="General cargo",
        weight_kg=Decimal("100"),
        volume_cbm=Decimal("0.2"),
        incoterm="DAP",
    )
    defaults.update(overrides)
    payload = InquiryCreate(customer_id=customer.id, **defaults)
    return create_inquiry(session, payload)


def simple_rate_card(session: Session, *, rate: Decimal = Decimal("5.00"), **rc_overrides) -> m.RateCard:
    """A rate card with a single unbounded per_kg break and no accessory
    charges — the baseline fixture for tests that don't care about break or
    charge details.
    """
    rate_card = make_rate_card(session, **rc_overrides)
    add_break(session, rate_card, min_weight=Decimal("0"), max_weight=None, rate=rate)
    return rate_card


def make_area(
    session: Session, stage: ShipmentStage, *, mode: TransportMode = TransportMode.AIR, **overrides
) -> m.Area:
    existing = session.execute(
        select(m.Area).where(m.Area.stage == stage, m.Area.mode == mode)
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    defaults = dict(name=f"{mode.value}-{stage.value}-area")
    defaults.update(overrides)
    area = m.Area(stage=stage, mode=mode, **defaults)
    session.add(area)
    session.flush()
    return area


def make_worker(session: Session, area: m.Area, *, password: str = "Worker123!", **overrides) -> m.Worker:
    defaults = dict(
        name="Test Worker",
        username=f"worker-{uuid.uuid4().hex[:10]}",
        password_hash=hash_password(password),
        area_id=area.id,
    )
    defaults.update(overrides)
    worker = m.Worker(**defaults)
    session.add(worker)
    session.flush()
    return worker
