from datetime import date

import pytest

from utils.errors import InvalidDocument
from models.enums import EventSource, ShipmentStage
from services.documents import get_document, list_documents, upload_document
from services.quotes import accept_quote, generate_quote
from services.transitions import advance_stage
from factories import make_customer, make_inquiry, simple_rate_card

TODAY = date(2026, 6, 1)

VALID_PDF = b"%PDF-1.4\n%mock pdf content for tests\n%%EOF"


def _accepted_shipment(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    return accept_quote(db_session, quote.id, "ops", today=TODAY)


def test_upload_accepts_valid_pdf(db_session):
    shipment = _accepted_shipment(db_session)

    document = upload_document(
        db_session, shipment, filename="airway-bill.pdf", content_type="application/pdf", data=VALID_PDF, actor="ops",
    )

    assert document.id is not None
    assert document.filename == "airway-bill.pdf"
    assert document.size_bytes == len(VALID_PDF)
    assert document.stage == shipment.stage


def test_upload_rejects_wrong_content_type(db_session):
    shipment = _accepted_shipment(db_session)
    with pytest.raises(InvalidDocument):
        upload_document(
            db_session, shipment, filename="notes.txt", content_type="text/plain", data=b"hello", actor="ops",
        )


def test_upload_rejects_bad_magic_bytes(db_session):
    shipment = _accepted_shipment(db_session)
    with pytest.raises(InvalidDocument):
        upload_document(
            db_session, shipment, filename="fake.pdf", content_type="application/pdf", data=b"not a real pdf", actor="ops",
        )


def test_upload_rejects_empty_file(db_session):
    shipment = _accepted_shipment(db_session)
    with pytest.raises(InvalidDocument):
        upload_document(
            db_session, shipment, filename="empty.pdf", content_type="application/pdf", data=b"", actor="ops",
        )


def test_upload_rejects_oversized_file(db_session):
    shipment = _accepted_shipment(db_session)
    oversized = VALID_PDF + b"0" * (4 * 1024 * 1024)
    with pytest.raises(InvalidDocument):
        upload_document(
            db_session, shipment, filename="huge.pdf", content_type="application/pdf", data=oversized, actor="ops",
        )


def test_upload_snapshots_current_stage_not_a_live_reference(db_session):
    shipment = _accepted_shipment(db_session)

    first = upload_document(
        db_session, shipment, filename="job-opening.pdf", content_type="application/pdf", data=VALID_PDF, actor="ops",
    )
    advance_stage(db_session, shipment, ShipmentStage.AIRWAY_BILL, actor="ops", note=None, source=EventSource.MANUAL)
    second = upload_document(
        db_session, shipment, filename="airway-bill.pdf", content_type="application/pdf", data=VALID_PDF, actor="ops",
    )

    assert first.stage == ShipmentStage.JOB_OPENING
    assert second.stage == ShipmentStage.AIRWAY_BILL


def test_list_documents_returns_only_this_shipments_documents(db_session):
    shipment_a = _accepted_shipment(db_session)
    shipment_b = _accepted_shipment(db_session)
    upload_document(db_session, shipment_a, filename="a.pdf", content_type="application/pdf", data=VALID_PDF, actor="ops")
    upload_document(db_session, shipment_b, filename="b.pdf", content_type="application/pdf", data=VALID_PDF, actor="ops")

    docs = list_documents(db_session, shipment_a.id)

    assert [d.filename for d in docs] == ["a.pdf"]


def test_get_document_returns_full_row_including_bytes(db_session):
    shipment = _accepted_shipment(db_session)
    uploaded = upload_document(db_session, shipment, filename="a.pdf", content_type="application/pdf", data=VALID_PDF, actor="ops")

    fetched = get_document(db_session, uploaded.id)

    assert fetched.data == VALID_PDF


def test_upload_endpoint_and_list_endpoint(client, db_session):
    shipment = _accepted_shipment(db_session)
    db_session.commit()

    r = client.post(
        f"/shipments/{shipment.id}/documents",
        files={"file": ("airway-bill.pdf", VALID_PDF, "application/pdf")},
    )
    assert r.status_code == 201, r.text
    assert r.json()["filename"] == "airway-bill.pdf"
    assert "data" not in r.json()

    r = client.get(f"/shipments/{shipment.id}/documents")
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1


def test_upload_endpoint_rejects_non_pdf(client, db_session):
    shipment = _accepted_shipment(db_session)
    db_session.commit()

    r = client.post(
        f"/shipments/{shipment.id}/documents",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 422, r.text


def test_download_endpoint_returns_pdf_bytes(client, db_session):
    shipment = _accepted_shipment(db_session)
    db_session.commit()

    upload = client.post(
        f"/shipments/{shipment.id}/documents",
        files={"file": ("airway-bill.pdf", VALID_PDF, "application/pdf")},
    )
    document_id = upload.json()["id"]

    r = client.get(f"/documents/{document_id}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content == VALID_PDF
