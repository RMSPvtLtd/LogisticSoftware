"""The customer-facing surface: a logged-in customer's own shipments and
quotes. Every route requires `get_current_customer`, and every query is
scoped to that customer's id via `services.customers` -- there is no
route here that accepts a customer_id from the request, so one customer can
never address another customer's data by guessing an id.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from utils.errors import NotFound
from models.customer import Customer
from models.quote import Quote
from models.shipment import Shipment
from schemas.auth import LoginRequest
from schemas.customer_portal import CustomerLoginResponse, CustomerShipmentSummary, shipment_summary
from schemas.customers import CustomerRead
from schemas.quotes import QuoteRead
from schemas.tracking import TrackingResult, from_shipment
from utils.security import create_access_token, get_current_customer
from services.customers import authenticate_customer, customer_quotes, customer_shipments

router = APIRouter(prefix="/customer", tags=["customer-portal"])


@router.post("/login", response_model=CustomerLoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> CustomerLoginResponse:
    customer = authenticate_customer(db, payload.username, payload.password)
    token = create_access_token(customer.id, "customer")
    return CustomerLoginResponse(access_token=token, customer=customer)


@router.get("/me", response_model=CustomerRead)
def me(customer: Customer = Depends(get_current_customer)) -> Customer:
    return customer


@router.get("/shipments", response_model=list[CustomerShipmentSummary])
def list_shipments(
    completed: bool | None = None,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> list[CustomerShipmentSummary]:
    return [shipment_summary(s) for s in customer_shipments(db, customer, completed=completed)]


@router.get("/shipments/{shipment_id}", response_model=TrackingResult)
def get_shipment(
    shipment_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> TrackingResult:
    shipment = db.get(Shipment, shipment_id)
    if shipment is None or shipment.customer_id != customer.id:
        # Same response for "doesn't exist" and "isn't yours" -- never
        # confirms another customer's shipment id is valid.
        raise NotFound(f"Shipment {shipment_id} not found")
    return from_shipment(shipment)


@router.get("/quotes", response_model=list[QuoteRead])
def list_quotes(
    customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)
) -> list[Quote]:
    return customer_quotes(db, customer)


@router.get("/quotes/{quote_id}", response_model=QuoteRead)
def get_quote(
    quote_id: int, customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)
) -> Quote:
    quote = db.get(Quote, quote_id)
    if quote is None or quote.inquiry.customer_id != customer.id:
        raise NotFound(f"Quote {quote_id} not found")
    return quote
