from datetime import date, datetime, timezone

import pytest

from app.adapters.mock import MockTrackingAdapter
from app.adapters.tracking import NormalizedStatus
from app.errors import TrackingIngestionFailed
from app.models.enums import EventSource, ShipmentStage
from app.services.quotes import accept_quote, generate_quote
from app.services.tracking import ingest_adapter_update
from app.services.transitions import advance_stage
from tests.factories import make_customer, make_inquiry, simple_rate_card

TODAY = date(2026, 6, 1)


def _accepted_shipment(db_session):
    customer = make_customer(db_session)
    simple_rate_card(db_session)
    inquiry = make_inquiry(db_session, customer)
    quote = generate_quote(db_session, inquiry.id, today=TODAY)
    db_session.flush()
    return accept_quote(db_session, quote.id, "ops", today=TODAY)


def test_valid_automated_update_goes_through_transition_service(db_session):
    shipment = _accepted_shipment(db_session)
    adapter = MockTrackingAdapter(
        {
            "REF1": NormalizedStatus(
                stage=ShipmentStage.DOCS_FILED,
                occurred_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
                note="Docs filed by carrier system",
                provider_reference="REF1",
            )
        }
    )

    event = ingest_adapter_update(db_session, shipment, adapter, "REF1")

    assert event is not None
    assert event.source == EventSource.AUTOMATED
    assert shipment.stage == ShipmentStage.DOCS_FILED


def test_no_status_from_adapter_is_a_noop(db_session):
    shipment = _accepted_shipment(db_session)
    adapter = MockTrackingAdapter({})

    result = ingest_adapter_update(db_session, shipment, adapter, "UNKNOWN")

    assert result is None
    assert shipment.stage == ShipmentStage.JOB_OPENED


def test_invalid_stage_from_adapter_does_not_mutate_shipment(db_session):
    shipment = _accepted_shipment(db_session)
    # Shipment is at job_opened; a provider reporting "delivered" is an
    # invalid skip-ahead and must be rejected without mutating anything.
    adapter = MockTrackingAdapter(
        {
            "REF2": NormalizedStatus(
                stage=ShipmentStage.DELIVERED,
                occurred_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
                note="Provider glitch",
                provider_reference="REF2",
            )
        }
    )

    with pytest.raises(TrackingIngestionFailed):
        ingest_adapter_update(db_session, shipment, adapter, "REF2")

    assert shipment.stage == ShipmentStage.JOB_OPENED
    assert len(shipment.status_events) == 1  # only the initial job_opened event


def test_backwards_stage_from_adapter_does_not_mutate_shipment(db_session):
    shipment = _accepted_shipment(db_session)
    advance_stage(db_session, shipment, ShipmentStage.DOCS_FILED, actor="ops", note=None, source=EventSource.MANUAL)
    advance_stage(db_session, shipment, ShipmentStage.PICKED_UP, actor="ops", note=None, source=EventSource.MANUAL)

    adapter = MockTrackingAdapter(
        {
            "REF3": NormalizedStatus(
                stage=ShipmentStage.DOCS_FILED,
                occurred_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
                note="Stale provider update",
                provider_reference="REF3",
            )
        }
    )

    with pytest.raises(TrackingIngestionFailed):
        ingest_adapter_update(db_session, shipment, adapter, "REF3")

    assert shipment.stage == ShipmentStage.PICKED_UP
