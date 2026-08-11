"""Sole owner of shipment stage ordering, labels, and grouping. Every other
module — the transition service, the tracking schema, `GET /meta/stages`,
and the frontend — reads stage order/labels/groups from here. Nothing else
re-encodes this ordering, so a stage can be added, relabeled, or regrouped
in exactly one place.

A shipment tracking row is created the moment an Inquiry is filed
(`services.inquiries.create_inquiry`) and moves through every stage below,
in order, starting at INQUIRY. There are no separate "pre-shipment" stages
anymore — Inquiry and Quotation are real, trackable Shipment stages.
"""

from enum import Enum


class TransportMode(str, Enum):
    AIR = "air"
    SEA = "sea"
    ROAD = "road"


class ShipmentStage(str, Enum):
    INQUIRY = "inquiry"
    QUOTATION = "quotation"
    JOB_OPENING = "job_opening"
    AIRWAY_BILL = "airway_bill"
    GD = "gd"
    PICKUP = "pickup"
    GATE_IN = "gate_in"
    SHIPMENT_RECEIPT = "shipment_receipt"
    WEIGHMENT = "weighment"
    CUSTOMS_EXAMINATION = "customs_examination"
    CUSTOMS_CLEARANCE = "customs_clearance"
    SCANNING = "scanning"
    HANDOVER = "handover"
    DEPARTURE = "departure"
    TRANSHIPMENT = "transhipment"
    ARRIVAL = "arrival"
    INVOICE_TO_CUSTOMER = "invoice_to_customer"


# The complete lifecycle, in order. Every Shipment moves through all of
# these, one at a time, starting at INQUIRY (index 0).
OPERATIONAL_STAGE_ORDER: tuple[ShipmentStage, ...] = (
    ShipmentStage.INQUIRY,
    ShipmentStage.QUOTATION,
    ShipmentStage.JOB_OPENING,
    ShipmentStage.AIRWAY_BILL,
    ShipmentStage.GD,
    ShipmentStage.PICKUP,
    ShipmentStage.GATE_IN,
    ShipmentStage.SHIPMENT_RECEIPT,
    ShipmentStage.WEIGHMENT,
    ShipmentStage.CUSTOMS_EXAMINATION,
    ShipmentStage.CUSTOMS_CLEARANCE,
    ShipmentStage.SCANNING,
    ShipmentStage.HANDOVER,
    ShipmentStage.DEPARTURE,
    ShipmentStage.TRANSHIPMENT,
    ShipmentStage.ARRIVAL,
    ShipmentStage.INVOICE_TO_CUSTOMER,
)

STAGE_LABELS: dict[ShipmentStage, str] = {
    ShipmentStage.INQUIRY: "Inquiry",
    ShipmentStage.QUOTATION: "Quotation",
    ShipmentStage.JOB_OPENING: "Job Opening",
    ShipmentStage.AIRWAY_BILL: "Airway Bill",
    ShipmentStage.GD: "GD (Goods Declaration)",
    ShipmentStage.PICKUP: "Pickup",
    ShipmentStage.GATE_IN: "Gate In",
    ShipmentStage.SHIPMENT_RECEIPT: "Shipment Receipt",
    ShipmentStage.WEIGHMENT: "Weighment",
    ShipmentStage.CUSTOMS_EXAMINATION: "Customs Examination",
    ShipmentStage.CUSTOMS_CLEARANCE: "Customs Clearance",
    ShipmentStage.SCANNING: "Scanning",
    ShipmentStage.HANDOVER: "Handover",
    ShipmentStage.DEPARTURE: "Departure",
    ShipmentStage.TRANSHIPMENT: "Transhipment",
    ShipmentStage.ARRIVAL: "Arrival",
    ShipmentStage.INVOICE_TO_CUSTOMER: "Invoice to Customer",
}

# Display-only grouping ("sub categories") for stages that belong to a
# named section of the pipeline. A stage not listed here is a standalone,
# top-level step. Purely presentational — it does not change ordering,
# transition rules, or worker-area assignment.
STAGE_GROUPS: dict[ShipmentStage, str] = {
    ShipmentStage.AIRWAY_BILL: "Documentation",
    ShipmentStage.GD: "Documentation",
    ShipmentStage.GATE_IN: "Airport",
    ShipmentStage.SHIPMENT_RECEIPT: "Airport",
    ShipmentStage.WEIGHMENT: "Airport",
    ShipmentStage.CUSTOMS_EXAMINATION: "Airport",
    ShipmentStage.CUSTOMS_CLEARANCE: "Airport",
    ShipmentStage.SCANNING: "Airport",
    ShipmentStage.HANDOVER: "Airport",
    ShipmentStage.DEPARTURE: "Airline",
    ShipmentStage.TRANSHIPMENT: "Airline",
    ShipmentStage.ARRIVAL: "Airline",
}


# Per-mode overrides for the handful of stage labels/groups that are
# air-flavored by default. Sea walks the exact same OPERATIONAL_STAGE_ORDER
# as air (same stage enum members, same transition rules) -- only the
# display text differs: the transport document is a "Bill of Lading" not an
# "Airway Bill", and the physical location groups are "Port"/"Carrier" not
# "Airport"/"Airline". Any stage/mode not listed here falls back to
# STAGE_LABELS / STAGE_GROUPS unchanged, so air's output is untouched.
STAGE_LABEL_OVERRIDES_BY_MODE: dict[TransportMode, dict[ShipmentStage, str]] = {
    TransportMode.SEA: {
        ShipmentStage.AIRWAY_BILL: "Bill of Lading",
    },
}

STAGE_GROUP_OVERRIDES_BY_MODE: dict[TransportMode, dict[ShipmentStage, str]] = {
    TransportMode.SEA: {
        ShipmentStage.GATE_IN: "Port",
        ShipmentStage.SHIPMENT_RECEIPT: "Port",
        ShipmentStage.WEIGHMENT: "Port",
        ShipmentStage.CUSTOMS_EXAMINATION: "Port",
        ShipmentStage.CUSTOMS_CLEARANCE: "Port",
        ShipmentStage.SCANNING: "Port",
        ShipmentStage.HANDOVER: "Port",
        ShipmentStage.DEPARTURE: "Carrier",
        ShipmentStage.TRANSHIPMENT: "Carrier",
        ShipmentStage.ARRIVAL: "Carrier",
    },
}


def stage_label(stage: ShipmentStage, mode: TransportMode | None = None) -> str:
    """Human-readable label for a stage, e.g. customs_examination -> 'Customs Examination'.
    Pass `mode` to get that mode's label where it differs from air's default
    (e.g. AIRWAY_BILL -> "Bill of Lading" for sea)."""
    if mode is not None:
        override = STAGE_LABEL_OVERRIDES_BY_MODE.get(mode, {}).get(stage)
        if override is not None:
            return override
    return STAGE_LABELS[stage]


def stage_group(stage: ShipmentStage, mode: TransportMode | None = None) -> str | None:
    """The display section a stage belongs to (e.g. 'Airport'), or None for
    a standalone stage. Pass `mode` to get that mode's group where it
    differs from air's default (e.g. "Airport" -> "Port" for sea)."""
    if mode is not None:
        override = STAGE_GROUP_OVERRIDES_BY_MODE.get(mode, {}).get(stage)
        if override is not None:
            return override
    return STAGE_GROUPS.get(stage)


def stage_index(stage: ShipmentStage) -> int:
    """Position of `stage` within the lifecycle (inquiry=0)."""
    return OPERATIONAL_STAGE_ORDER.index(stage)


def next_stage(stage: ShipmentStage) -> ShipmentStage | None:
    """The immediate next stage, or None if `stage` is terminal."""
    idx = stage_index(stage)
    if idx + 1 >= len(OPERATIONAL_STAGE_ORDER):
        return None
    return OPERATIONAL_STAGE_ORDER[idx + 1]


def previous_stage(stage: ShipmentStage) -> ShipmentStage | None:
    """The immediate previous stage, or None if `stage` is INQUIRY (nothing
    precedes it — a Shipment is created there directly by
    `services.inquiries.create_inquiry`)."""
    idx = stage_index(stage)
    if idx == 0:
        return None
    return OPERATIONAL_STAGE_ORDER[idx - 1]


# Stages produced automatically by application events rather than a person
# marking them done: INQUIRY at shipment creation, QUOTATION when a quote is
# generated, JOB_OPENING when a quote is accepted (services.quotes).
SYSTEM_DRIVEN_STAGES: tuple[ShipmentStage, ...] = (
    ShipmentStage.INQUIRY,
    ShipmentStage.QUOTATION,
    ShipmentStage.JOB_OPENING,
)

# Stages a worker Area can be responsible for -- everything between the
# system-driven stages and the ops-only final invoicing step. Each of these
# gets its own Area (see app.models.worker) and worker queue.
WORKER_ASSIGNABLE_STAGES: tuple[ShipmentStage, ...] = tuple(
    s
    for s in OPERATIONAL_STAGE_ORDER
    if s not in SYSTEM_DRIVEN_STAGES and s != ShipmentStage.INVOICE_TO_CUSTOMER
)

# Valid targets for services.transitions.correct_stage -- once a job exists
# (job_opening onward). Correcting "back" to inquiry/quotation doesn't make
# operational sense once a job number has been issued.
CORRECTABLE_STAGES: tuple[ShipmentStage, ...] = tuple(
    s for s in OPERATIONAL_STAGE_ORDER if stage_index(s) >= stage_index(ShipmentStage.JOB_OPENING)
)


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
