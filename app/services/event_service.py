from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid

from app.db.models import Event
from app.db.schemas import EventCreate, EventOut


def log_event(db: Session, payload: EventCreate) -> EventOut:
    event = Event(
        event_id=str(uuid.uuid4()),
        user_id=payload.user_id,
        experiment_id=payload.experiment_id,
        event_name=payload.event_name,
        event_value=payload.event_value,
        event_time=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return EventOut(
        event_id=event.event_id,
        user_id=event.user_id,
        experiment_id=event.experiment_id,
        event_name=event.event_name,
        event_value=event.event_value,
        event_time=event.event_time,
    )
