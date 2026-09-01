"""Airline weekly-schedule CRUD -- a flat reference list, no owned child rows
to diff (unlike rate cards' breaks/charges), so this is even simpler than
services.rate_cards."""

import json

from sqlalchemy.orm import Session

from models.airline_schedule import AirlineSchedule
from schemas.airline_schedules import AirlineScheduleCreate
from utils.errors import NotFound


def _apply(schedule: AirlineSchedule, payload: AirlineScheduleCreate) -> None:
    schedule.airline_name = payload.airline_name
    schedule.origin = payload.origin
    schedule.destination = payload.destination
    schedule.mode = payload.mode
    schedule.days_of_week = json.dumps(payload.days_of_week)
    schedule.notes = payload.notes


def create_airline_schedule(session: Session, payload: AirlineScheduleCreate) -> AirlineSchedule:
    schedule = AirlineSchedule()
    _apply(schedule, payload)
    session.add(schedule)
    session.flush()
    return schedule


def get_airline_schedule(session: Session, schedule_id: int) -> AirlineSchedule:
    schedule = session.get(AirlineSchedule, schedule_id)
    if schedule is None:
        raise NotFound(f"Airline schedule {schedule_id} not found")
    return schedule


def update_airline_schedule(session: Session, schedule_id: int, payload: AirlineScheduleCreate) -> AirlineSchedule:
    schedule = get_airline_schedule(session, schedule_id)
    _apply(schedule, payload)
    session.flush()
    return schedule


def delete_airline_schedule(session: Session, schedule_id: int) -> None:
    schedule = get_airline_schedule(session, schedule_id)
    session.delete(schedule)
    session.flush()
