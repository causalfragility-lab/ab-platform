from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.result_service import compute_results

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/{experiment_id}")
def get_results(experiment_id: str, db: Session = Depends(get_db)):
    """
    Returns full inference output: lift, CI, p-value, SRM check,
    fragility warnings, daily trends, and interpretation.
    """
    try:
        return compute_results(db, experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
