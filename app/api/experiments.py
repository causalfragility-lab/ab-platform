from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from datetime import datetime, timezone
from typing import List

from app.db.session import get_db
from app.db.models import Experiment, Variant
from app.db.schemas import ExperimentCreate, ExperimentOut

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentOut)
def create_experiment(payload: ExperimentCreate, db: Session = Depends(get_db)):
    total_weight = sum(v.allocation_weight for v in payload.variants)
    if abs(total_weight - 1.0) > 1e-6:
        raise HTTPException(status_code=400, detail=f"Variant weights must sum to 1.0 (got {total_weight:.4f})")
    if len(payload.variants) < 2:
        raise HTTPException(status_code=400, detail="At least 2 variants required")

    exp_id = f"exp_{uuid.uuid4().hex[:8]}"
    experiment = Experiment(
        experiment_id=exp_id,
        name=payload.name,
        description=payload.description,
        metric_name=payload.metric_name,
        metric_type=payload.metric_type,
        allocation=payload.allocation,
        status="draft",
    )
    db.add(experiment)
    db.flush()

    for v in payload.variants:
        variant = Variant(
            variant_id=f"var_{uuid.uuid4().hex[:8]}",
            experiment_id=exp_id,
            name=v.name,
            allocation_weight=v.allocation_weight,
        )
        db.add(variant)

    db.commit()
    db.refresh(experiment)
    return experiment


@router.get("", response_model=List[ExperimentOut])
def list_experiments(db: Session = Depends(get_db)):
    return db.query(Experiment).all()


@router.get("/{experiment_id}", response_model=ExperimentOut)
def get_experiment(experiment_id: str, db: Session = Depends(get_db)):
    exp = db.query(Experiment).filter(Experiment.experiment_id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@router.patch("/{experiment_id}/status")
def update_status(experiment_id: str, status: str, db: Session = Depends(get_db)):
    valid = {"draft", "running", "paused", "completed"}
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {valid}")
    exp = db.query(Experiment).filter(Experiment.experiment_id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    exp.status = status
    if status == "running" and not exp.start_date:
        exp.start_date = datetime.now(timezone.utc)
    if status == "completed":
        exp.end_date = datetime.now(timezone.utc)
    db.commit()
    return {"experiment_id": experiment_id, "status": status}


@router.delete("/{experiment_id}")
def delete_experiment(experiment_id: str, db: Session = Depends(get_db)):
    exp = db.query(Experiment).filter(Experiment.experiment_id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    db.delete(exp)
    db.commit()
    return {"deleted": experiment_id}
