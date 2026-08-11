"""Customer portal accounts and the scoped queries behind them.
`grant_portal_access` is the only way a Customer gets a username -- there is
no self-service signup in this MVP; ops issues credentials on request (see
`app.api.customers`). `customer_shipments`/`customer_quotes` are the sole
place ownership scoping happens: every customer-portal route in
`app.api.customer_portal` goes through one of these rather than filtering
a general query by an ID the client could tamper with.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import Unauthorized
from app.models.customer import Customer
from app.models.enums import ShipmentStage
from app.models.inquiry import Inquiry
from app.models.quote import Quote
from app.models.shipment import Shipment
from app.security import hash_password, verify_password


def authenticate_customer(session: Session, username: str, password: str) -> Customer:
    customer = session.execute(select(Customer).where(Customer.username == username)).scalar_one_or_none()
    if (
        customer is None
        or not customer.portal_active
        or customer.password_hash is None
        or not verify_password(password, customer.password_hash)
    ):
        # Deliberately the same message for "no such user", "wrong password",
        # and "deactivated" -- doesn't tell a caller which one it was.
        raise Unauthorized("Invalid username or password.")
    return customer


def grant_portal_access(session: Session, customer: Customer, *, username: str, password: str) -> Customer:
    customer.username = username
    customer.password_hash = hash_password(password)
    customer.portal_active = True
    session.flush()
    return customer


def set_portal_active(session: Session, customer: Customer, is_active: bool) -> Customer:
    customer.portal_active = is_active
    session.flush()
    return customer


def customer_shipments(session: Session, customer: Customer, *, completed: bool | None = None) -> list[Shipment]:
    stmt = select(Shipment).where(Shipment.customer_id == customer.id)
    if completed is True:
        stmt = stmt.where(Shipment.stage == ShipmentStage.INVOICE_TO_CUSTOMER)
    elif completed is False:
        stmt = stmt.where(Shipment.stage != ShipmentStage.INVOICE_TO_CUSTOMER)
    return list(session.execute(stmt.order_by(Shipment.updated_at.desc())).scalars())


def customer_quotes(session: Session, customer: Customer) -> list[Quote]:
    stmt = (
        select(Quote)
        .join(Inquiry, Inquiry.id == Quote.inquiry_id)
        .where(Inquiry.customer_id == customer.id)
        .order_by(Quote.created_at.desc())
    )
    return list(session.execute(stmt).scalars())
