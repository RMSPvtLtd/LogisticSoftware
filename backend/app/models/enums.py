"""Sole owner of shipment stage ordering, labels, and the operational sequence
used by the customer tracking checklist. Every other module — the transition
service, the tracking schema, `GET /meta/stages`, and eventually the frontend —
reads stage order and labels from here. Nothing else re-encodes this ordering,
so a stage can be added or relabeled in exactly one place.
"""

from enum import Enum


class ShipmentStage(str, Enum):
    INQUIRY = "inquiry"
    QUOTED = "quoted"
    JOB_OPENED = "job_opened"
    DOCS_FILED = "docs_filed"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    CUSTOMS_CLEARANCE = "customs_clearance"
    ARRIVED = "arrived"
    DELIVERED = "delivered"


# Full lifecycle order, including the pre-shipment stages (inquiry, quoted)
# that exist conceptually but are never written to Shipment.stage — a
# Shipment is only ever created once a quote is accepted, starting at
# job_opened.
_FULL_STAGE_ORDER: tuple[ShipmentStage, ...] = (
    ShipmentStage.INQUIRY,
    ShipmentStage.QUOTED,
    ShipmentStage.JOB_OPENED,
    ShipmentStage.DOCS_FILED,
    ShipmentStage.PICKED_UP,
    ShipmentStage.IN_TRANSIT,
    ShipmentStage.CUSTOMS_CLEARANCE,
    ShipmentStage.ARRIVED,
    ShipmentStage.DELIVERED,
)

# The operational sequence a Shipment actually moves through, and the sequence
# the customer tracking checklist is built from. Starts at job_opened because
# that is the stage a Shipment is created at.
OPERATIONAL_STAGE_ORDER: tuple[ShipmentStage, ...] = tuple(
    stage for stage in _FULL_STAGE_ORDER if stage != ShipmentStage.INQUIRY and stage != ShipmentStage.QUOTED
)

STAGE_LABELS: dict[ShipmentStage, str] = {
    ShipmentStage.INQUIRY: "Inquiry",
    ShipmentStage.QUOTED: "Quoted",
    ShipmentStage.JOB_OPENED: "Job Opened",
    ShipmentStage.DOCS_FILED: "Documentation Filed",
    ShipmentStage.PICKED_UP: "Picked Up",
    ShipmentStage.IN_TRANSIT: "In Transit",
    ShipmentStage.CUSTOMS_CLEARANCE: "Customs Clearance",
    ShipmentStage.ARRIVED: "Arrived",
    ShipmentStage.DELIVERED: "Delivered",
}


def stage_label(stage: ShipmentStage) -> str:
    """Human-readable label for a stage, e.g. in_transit -> 'In Transit'."""
    return STAGE_LABELS[stage]


def stage_index(stage: ShipmentStage) -> int:
    """Position of `stage` within the operational sequence (job_opened=0)."""
    return OPERATIONAL_STAGE_ORDER.index(stage)


def next_stage(stage: ShipmentStage) -> ShipmentStage | None:
    """The immediate next operational stage, or None if `stage` is terminal."""
    idx = stage_index(stage)
    if idx + 1 >= len(OPERATIONAL_STAGE_ORDER):
        return None
    return OPERATIONAL_STAGE_ORDER[idx + 1]


def previous_stage(stage: ShipmentStage) -> ShipmentStage | None:
    """The immediate previous operational stage, or None if `stage` is job_opened
    (nothing precedes it — a Shipment is created there by quote acceptance,
    not advanced into it by a worker)."""
    idx = stage_index(stage)
    if idx == 0:
        return None
    return OPERATIONAL_STAGE_ORDER[idx - 1]


# Stages a worker Area can be responsible for producing. job_opened is
# excluded -- it is created by quote acceptance (services.quotes.accept_quote),
# never by a worker completing a queue item.
WORKER_ASSIGNABLE_STAGES: tuple[ShipmentStage, ...] = OPERATIONAL_STAGE_ORDER[1:]


class TransportMode(str, Enum):
    AIR = "air"
    SEA = "sea"
    ROAD = "road"


class QuoteStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    EXPIRED = "expired"


class EventSource(str, Enum):
    MANUAL = "manual"
    AUTOMATED = "automated"
    SYSTEM = "system"
    CORRECTION = "correction"


class ReferenceType(str, Enum):
    JOB_NUMBER = "JOB_NUMBER"
    MAWB = "MAWB"
    HAWB = "HAWB"
    MBL = "MBL"
    HBL = "HBL"
    CONTAINER = "CONTAINER"


class ChargeKind(str, Enum):
    FREIGHT = "freight"
    DOCUMENTATION = "documentation"
    CUSTOMS = "customs"
    PICKUP = "pickup"
    HANDLING = "handling"
    OTHER = "other"


class ChargeBasis(str, Enum):
    FLAT = "flat"
    PER_KG = "per_kg"
    PERCENT_OF_FREIGHT = "percent_of_freight"


class UnitOfMeasure(str, Enum):
    PER_KG = "per_kg"
    PER_CBM = "per_cbm"
    FLAT = "flat"
