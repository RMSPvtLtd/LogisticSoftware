from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models.airline_schedule import AirlineSchedule
from schemas.airline_schedules import AirlineScheduleCreate, AirlineScheduleRead
from services.airline_schedules import (
    create_airline_schedule,
    delete_airline_schedule,
    get_airline_schedule,
    update_airline_schedule,
)
from utils.security import get_current_ops_user

router = APIRouter(
    prefix="/airline-schedules", tags=["airline-schedules"], dependencies=[Depends(get_current_ops_user)]
)


@router.post("", response_model=AirlineScheduleRead, status_code=201)
def create_airline_schedule_route(payload: AirlineScheduleCreate, db: Session = Depends(get_db)) -> AirlineSchedule:
    return create_airline_schedule(db, payload)


@router.get("", response_model=list[AirlineScheduleRead])
def list_airline_schedules(db: Session = Depends(get_db)) -> list[AirlineSchedule]:
    stmt = select(AirlineSchedule).order_by(
        AirlineSchedule.origin, AirlineSchedule.destination, AirlineSchedule.airline_name
    )
    return list(db.execute(stmt).scalars())


@router.get("/{schedule_id}", response_model=AirlineScheduleRead)
def get_airline_schedule_route(schedule_id: int, db: Session = Depends(get_db)) -> AirlineSchedule:
    return get_airline_schedule(db, schedule_id)


@router.patch("/{schedule_id}", response_model=AirlineScheduleRead)
def update_airline_schedule_route(
    schedule_id: int, payload: AirlineScheduleCreate, db: Session = Depends(get_db)
) -> AirlineSchedule:
    return update_airline_schedule(db, schedule_id, payload)


@router.delete("/{schedule_id}", status_code=204)
def delete_airline_schedule_route(schedule_id: int, db: Session = Depends(get_db)) -> None:
    delete_airline_schedule(db, schedule_id)
