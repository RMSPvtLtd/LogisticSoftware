from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotFound
from app.models.customer import Customer
from app.schemas.customers import CustomerCreate, CustomerPortalCredentials, CustomerPortalUpdate, CustomerRead
from app.services.customers import grant_portal_access, set_portal_active

router = APIRouter(prefix="/customers", tags=["customers"])


def _get_customer(db: Session, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise NotFound(f"Customer {customer_id} not found")
    return customer


@router.post("", response_model=CustomerRead, status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)) -> Customer:
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.flush()
    return customer


@router.get("", response_model=list[CustomerRead])
def list_customers(db: Session = Depends(get_db)) -> list[Customer]:
    return list(db.execute(select(Customer).order_by(Customer.id)).scalars())


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, db: Session = Depends(get_db)) -> Customer:
    return _get_customer(db, customer_id)


@router.post("/{customer_id}/portal-access", response_model=CustomerRead)
def grant_customer_portal_access(
    customer_id: int, payload: CustomerPortalCredentials, db: Session = Depends(get_db)
) -> Customer:
    """Ops-only: issues (or resets) a customer's portal login. Not a
    self-service signup -- there is no route a customer can call to create
    or change their own username/password."""
    customer = _get_customer(db, customer_id)
    return grant_portal_access(db, customer, username=payload.username, password=payload.password)


@router.patch("/{customer_id}/portal-access", response_model=CustomerRead)
def update_customer_portal_access(
    customer_id: int, payload: CustomerPortalUpdate, db: Session = Depends(get_db)
) -> Customer:
    customer = _get_customer(db, customer_id)
    return set_portal_active(db, customer, payload.is_active)
