from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import RuntimeState


POOL_STATE_KEY = "database_pool_size"
BASELINE_POOL_SIZE = 20
EXPANDED_POOL_SIZE = 40


def get_pool_size(session: Session) -> int:
    """Return the persistent simulated database pool size, creating its baseline."""
    state = session.get(RuntimeState, POOL_STATE_KEY)
    if state is None:
        state = RuntimeState(key=POOL_STATE_KEY, pool_size=BASELINE_POOL_SIZE)
        session.add(state)
        session.commit()
        session.refresh(state)
    return state.pool_size


def set_pool_size(session: Session, pool_size: int) -> int:
    state = session.get(RuntimeState, POOL_STATE_KEY)
    if state is None:
        state = RuntimeState(key=POOL_STATE_KEY, pool_size=pool_size)
        session.add(state)
    else:
        state.pool_size = pool_size
    session.flush()
    return pool_size


def reset_pool_size(session: Session) -> tuple[int, int]:
    previous = get_pool_size(session)
    set_pool_size(session, BASELINE_POOL_SIZE)
    session.commit()
    return previous, BASELINE_POOL_SIZE
