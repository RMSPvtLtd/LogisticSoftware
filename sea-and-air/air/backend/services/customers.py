"""Customer portal accounts and the scoped queries behind them.
`grant_portal_access` is the only way a Customer gets a username -- there is
no self-service signup in this MVP; ops issues credentials on request (see
`api.customers`). `customer_shipments`/`customer_quotes` are the sole
place ownership scoping happens: every customer-portal route in
`api.customer_portal` goes through one of these rather than filtering
a general query by an ID the client could tamper with.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from utils.errors import DuplicateCustomerEmail, Unauthorized
from models.customer import Customer
from models.enums import ShipmentStage
from models.inquiry import Inquiry
from models.quote import Quote
from models.shipment import Shipment
from utils.security import hash_password, verify_password


def create_customer(
    session: Session,
    *,
    name: str,
    email: str,
    company_name: str | None = None,
    phone: str | None = None,
    address: str | None = None,
) -> Customer:
    """Checks for an existing customer with this email before inserting, so
    the caller gets a specific DuplicateCustomerEmail (naming the existing
    customer) instead of the generic IntegrityError 409 that a bare unique
    constraint violation would otherwise surface as."""
    existing = session.execute(select(Customer).where(Customer.email == email)).scalar_one_or_none()
    if existing is not None:
        raise DuplicateCustomerEmail(
            f"A customer with email {email} already exists: {existing.name} (ID {existing.id}).",
            customer_id=existing.id,
            customer_name=existing.name,
        )
    customer = Customer(name=name, email=email, company_name=company_name, phone=phone, address=address)
    session.add(customer)
    session.flush()
    return customer


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
