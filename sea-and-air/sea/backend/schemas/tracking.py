"""The provider-independent tracking model. Nothing downstream of a
provider connector (the tracking service, the API, the frontend) ever sees
a provider's raw field names -- every connector's job is to produce exactly
this shape. Adding a second provider (KICT, QICT, a shipping line, customs)
means adding a second connector that fills in the same `TrackingResult`,
never widening this schema with provider-specific fields.
"""

from pydantic import BaseModel, Field


class ContainerTrackingRequest(BaseModel):
    container_number: str = Field(min_length=1)


class TrackingEvent(BaseModel):
    type: str
    timestamp: str | None


class ContainerDetail(BaseModel):
    """The richer per-voyage detail SAPT exposes behind a second request
    (ContainerDetails, keyed by the pid a ContainerHistory record carries).
    One container can have several of these -- one per voyage/cycle it has
    been through (e.g. an earlier import leg and a later export leg) -- so
    TrackingResult carries a list, not a single detail.
    """

    owner: str | None = None
    bl_number: str | None = None
    container_size_type: str | None = None
    category: str | None = None
    status_code: str | None = None
    vessel_voyage: str | None = None
    vir_number: str | None = None
    eta: str | None = None
    etd: str | None = None
    discharge_time: str | None = None
    load_time: str | None = None
    do_issuance_date: str | None = None
    do_expiry_date: str | None = None
    gate_in_time: str | None = None
    gate_out_time: str | None = None
    origin: str | None = None
    destination: str | None = None
    custom_seal_number: str | None = None
    line_seal_number: str | None = None
    security_seal_number: str | None = None
    other_seal_number: str | None = None
    custom_status: str | None = None
    current_position: str | None = None
    commodity: str | None = None
    weight: str | None = None
    weighment: str | None = None
    scanning: str | None = None
    present_holds: str | None = None


class TrackingResult(BaseModel):
    provider: str
    terminal: str
    container_number: str
    status: str
    status_code: str | None = None
    events: list[TrackingEvent]
    details: list[ContainerDetail] = []
