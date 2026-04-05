from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.schemas import AssignmentOut, EventCreate, EventOut
from app.services.assignment_service import get_or_create_assignment
from app.services.event_service import log_event

router = APIRouter(tags=["assignment & events"])


@router.get("/assign", response_model=AssignmentOut)
def assign_user(
    experiment_id: str = Query(...),
    user_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Deterministically assign a user to a variant.
    Same user + experiment always returns the same variant.
    """
    try:
        return get_or_create_assignment(db, user_id, experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/events", response_model=EventOut)
def record_event(payload: EventCreate, db: Session = Depends(get_db)):
    """Log an outcome event (exposure, conversion, revenue, session_length)."""
    return log_event(db, payload)
