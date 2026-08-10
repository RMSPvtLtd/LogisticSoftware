"""There is no authentication in this MVP. `current_actor` is the single,
isolated place that resolves who to record on a status event; replacing it
with real authentication later means changing this one function, not every
endpoint that accepts an actor.
"""

from fastapi import Header

from app.config import get_settings


def current_actor(x_actor: str | None = Header(default=None)) -> str:
    return x_actor or get_settings().default_actor
