"""Worker accounts, area assignment, and the worker's queue/complete
actions. `complete_worker_stage` is a thin, named wrapper around
`services.transitions.advance_stage` — the restriction to "only your area's
stage" falls directly out of passing `worker.area.stage` as the fixed
target: advance_stage already rejects anything that isn't the shipment's
immediate next stage, so a worker can never advance a shipment into any
stage but their own, without a second, parallel authorization check to
keep in sync with the transition rules.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from utils.errors import NotFound, Unauthorized
from models.document import ShipmentDocument
from models.enums import DocumentType, EventSource, previous_stage
from models.shipment import Shipment, StatusEvent
from models.worker import Area, Worker
from utils.security import hash_password, verify_password
from services.documents import list_documents, upload_document
from services.transitions import advance_stage


def authenticate_worker(session: Session, username: str, password: str) -> Worker:
    worker = session.execute(select(Worker).where(Worker.username == username)).scalar_one_or_none()
    if worker is None or not worker.is_active or not verify_password(password, worker.password_hash):
        # Deliberately the same message for "no such user", "wrong password",
        # and "deactivated" -- doesn't tell a caller which one it was.
        raise Unauthorized("Invalid username or password.")
    return worker


def create_worker(session: Session, *, name: str, username: str, password: str, area_id: int) -> Worker:
    if session.get(Area, area_id) is None:
        raise NotFound(f"Area {area_id} not found")
    worker = Worker(name=name, username=username, password_hash=hash_password(password), area_id=area_id)
    session.add(worker)
    session.flush()
    return worker


def worker_queue(session: Session, worker: Worker) -> list[Shipment]:
    """Shipments currently waiting to enter this worker's area stage,
    oldest-waiting first. Cancelled shipments are excluded entirely -- a
    worker simply never sees one, since there's nothing left to ever do on
    it. Held shipments stay visible (a hold is meant to be a visible, likely
    temporary pause) but advance_stage still refuses to complete one.
    """
    waiting_stage = previous_stage(worker.area.stage)
    if waiting_stage is None:
        return []
    stmt = (
        select(Shipment)
        .where(Shipment.stage == waiting_stage, ~Shipment.is_cancelled)
        .order_by(Shipment.updated_at)
    )
    return list(session.execute(stmt).scalars())


def completed_shipments(session: Session, worker: Worker) -> list[Shipment]:
    """Shipments this worker has personally advanced through their area's
    stage, most recently touched first -- the "Completed" counterpart to
    `worker_queue`'s "Remaining". Matched on the StatusEvent `complete_worker_stage`
    itself writes (stage=worker's area, actor=worker's name, is_stage_change),
    not on the shipment's current stage, so a shipment that has since moved
    further along -- or even been cancelled -- still shows up here as part
    of this worker's history.
    """
    completed_ids = select(StatusEvent.shipment_id).where(
        StatusEvent.stage == worker.area.stage,
        StatusEvent.actor == worker.name,
        StatusEvent.is_stage_change.is_(True),
    )
    stmt = select(Shipment).where(Shipment.id.in_(completed_ids)).order_by(Shipment.updated_at.desc())
    return list(session.execute(stmt).scalars())


def complete_worker_stage(
    session: Session, worker: Worker, shipment: Shipment, *, note: str | None
) -> StatusEvent:
    return advance_stage(
        session, shipment, worker.area.stage, actor=worker.name, note=note, source=EventSource.MANUAL
    )


def _assert_shipment_in_worker_queue(worker: Worker, shipment: Shipment) -> None:
    """Workers may only touch documents on a shipment currently in their own
    queue (waiting to enter their area's stage) -- the same scope
    `worker_queue` exposes and `complete_worker_stage` enforces via
    advance_stage's next-stage-only rule.
    """
    if shipment.stage != previous_stage(worker.area.stage):
        raise Unauthorized("This shipment is not currently in your queue.")


def upload_worker_document(
    session: Session,
    worker: Worker,
    shipment: Shipment,
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
    document_type: DocumentType | None = None,
) -> ShipmentDocument:
    _assert_shipment_in_worker_queue(worker, shipment)
    return upload_document(
        session, shipment, filename=filename, content_type=content_type, data=data,
        actor=worker.name, document_type=document_type,
    )


def list_worker_documents(session: Session, worker: Worker, shipment: Shipment) -> list[ShipmentDocument]:
    _assert_shipment_in_worker_queue(worker, shipment)
    return list_documents(session, shipment.id)
