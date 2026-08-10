from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotFound
from app.models.customer import Customer
from app.models.inquiry import Inquiry
from app.schemas.inquiries import InquiryCreate, InquiryRead

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


@router.post("", response_model=InquiryRead, status_code=201)
def create_inquiry(payload: InquiryCreate, db: Session = Depends(get_db)) -> Inquiry:
    if db.get(Customer, payload.customer_id) is None:
        raise NotFound(f"Customer {payload.customer_id} not found")
    inquiry = Inquiry(**payload.model_dump())
    db.add(inquiry)
    db.flush()
    return inquiry


@router.get("", response_model=list[InquiryRead])
def list_inquiries(db: Session = Depends(get_db)) -> list[Inquiry]:
    return list(db.execute(select(Inquiry).order_by(Inquiry.id)).scalars())


@router.get("/{inquiry_id}", response_model=InquiryRead)
def get_inquiry(inquiry_id: int, db: Session = Depends(get_db)) -> Inquiry:
    inquiry = db.get(Inquiry, inquiry_id)
    if inquiry is None:
        raise NotFound(f"Inquiry {inquiry_id} not found")
    return inquiry
