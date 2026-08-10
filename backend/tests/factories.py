"""Small object-creation helpers shared across tests. Not fixtures
themselves (fixtures own the session) — plain functions the tests call with
whatever session fixture they're using.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

import app.models as m
from app.models.enums import ChargeBasis, TransportMode, UnitOfMeasure


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
    inquiry = m.Inquiry(customer_id=customer.id, **defaults)
    session.add(inquiry)
    session.flush()
    return inquiry


def simple_rate_card(session: Session, *, rate: Decimal = Decimal("5.00"), **rc_overrides) -> m.RateCard:
    """A rate card with a single unbounded per_kg break and no accessory
    charges — the baseline fixture for tests that don't care about break or
    charge details.
    """
    rate_card = make_rate_card(session, **rc_overrides)
    add_break(session, rate_card, min_weight=Decimal("0"), max_weight=None, rate=rate)
    return rate_card
