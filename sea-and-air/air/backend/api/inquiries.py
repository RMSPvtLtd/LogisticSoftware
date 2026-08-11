from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from utils.errors import NotFound
from models.inquiry import Inquiry
from schemas.inquiries import InquiryCreate, InquiryRead
from services.inquiries import create_inquiry as create_inquiry_service

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


@router.post("", response_model=InquiryRead, status_code=201)
def create_inquiry(payload: InquiryCreate, db: Session = Depends(get_db)) -> Inquiry:
    return create_inquiry_service(db, payload)


@router.get("", response_model=list[InquiryRead])
def list_inquiries(db: Session = Depends(get_db)) -> list[Inquiry]:
    return list(db.execute(select(Inquiry).order_by(Inquiry.id)).scalars())


@router.get("/{inquiry_id}", response_model=InquiryRead)
def get_inquiry(inquiry_id: int, db: Session = Depends(get_db)) -> Inquiry:
    inquiry = db.get(Inquiry, inquiry_id)
    if inquiry is None:
        raise NotFound(f"Inquiry {inquiry_id} not found")
    return inquiry
