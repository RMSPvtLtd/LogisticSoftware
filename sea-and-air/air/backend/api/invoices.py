from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from db import get_db
from models.invoice import Invoice
from schemas.invoices import InvoiceCreateRequest, InvoiceRead
from services.invoices import create_invoice_from_quote, get_invoice, list_invoices
from services.pdf_documents import render_invoice_pdf

router = APIRouter(prefix="/invoices", tags=["invoices"])

# The "Create Invoice from Quote" action lives under /quotes, not /invoices --
# an invoice only ever comes into existence by converting a specific quote,
# so the URL reflects that relationship (mirrors POST /quotes/{id}/accept).
quote_router = APIRouter(prefix="/quotes", tags=["invoices"])


@quote_router.post("/{quote_id}/invoice", response_model=InvoiceRead, status_code=201)
def create_from_quote(quote_id: int, payload: InvoiceCreateRequest, db: Session = Depends(get_db)) -> Invoice:
    return create_invoice_from_quote(db, quote_id, company_id=payload.company_id)


@router.get("", response_model=list[InvoiceRead])
def list_all(db: Session = Depends(get_db)) -> list[Invoice]:
    return list_invoices(db)


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_one(invoice_id: int, db: Session = Depends(get_db)) -> Invoice:
    return get_invoice(db, invoice_id)


@router.get("/{invoice_id}/pdf")
def download_pdf(invoice_id: int, db: Session = Depends(get_db)) -> Response:
    invoice = get_invoice(db, invoice_id)
    pdf_bytes = render_invoice_pdf(invoice)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{invoice.invoice_number}.pdf"'},
    )
