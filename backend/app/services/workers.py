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

from app.errors import NotFound, Unauthorized
from app.models.enums import EventSource, previous_stage
from app.models.shipment import Shipment, StatusEvent
from app.models.worker import Area, Worker
from app.security import hash_password, verify_password
from app.services.transitions import advance_stage


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
    oldest-waiting first. Filtered to the area's mode too -- air and sea
    areas can own the same stage value (see app.models.worker.Area), so
    without this filter a sea customs officer's queue would include air
    shipments sitting at the same stage, and vice versa.
    """
    waiting_stage = previous_stage(worker.area.stage)
    if waiting_stage is None:
        return []
    stmt = (
        select(Shipment)
        .where(Shipment.stage == waiting_stage, Shipment.mode == worker.area.mode)
        .order_by(Shipment.updated_at)
    )
    return list(session.execute(stmt).scalars())


def complete_worker_stage(
    session: Session, worker: Worker, shipment: Shipment, *, note: str | None
) -> StatusEvent:
    return advance_stage(
        session, shipment, worker.area.stage, actor=worker.name, note=note, source=EventSource.MANUAL
    )
