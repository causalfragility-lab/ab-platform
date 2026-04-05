from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid

from app.db.models import Assignment, Experiment, Variant
from app.core.hashing import deterministic_hash
from app.db.schemas import AssignmentOut


def get_or_create_assignment(db: Session, user_id: str, experiment_id: str) -> AssignmentOut:
    # Check for existing assignment (no reassignment across sessions)
    existing = (
        db.query(Assignment)
        .filter(Assignment.user_id == user_id, Assignment.experiment_id == experiment_id)
        .first()
    )
    if existing:
        variant = db.query(Variant).filter(Variant.variant_id == existing.variant_id).first()
        return AssignmentOut(
            user_id=existing.user_id,
            experiment_id=existing.experiment_id,
            variant_id=existing.variant_id,
            variant_name=variant.name,
            assigned_at=existing.assigned_at,
        )

    experiment = db.query(Experiment).filter(Experiment.experiment_id == experiment_id).first()
    if not experiment:
        raise ValueError(f"Experiment {experiment_id} not found")
    if experiment.status != "running":
        raise ValueError(f"Experiment {experiment_id} is not running (status: {experiment.status})")

    variants = experiment.variants
    if not variants:
        raise ValueError(f"Experiment {experiment_id} has no variants")

    names = [v.name for v in variants]
    weights = [v.allocation_weight for v in variants]

    # Deterministic hash → bucket → variant
    bucket = deterministic_hash(user_id, experiment_id)
    cumulative = 0.0
    selected_variant = variants[-1]
    for v, w in zip(variants, weights):
        cumulative += w
        if bucket < cumulative:
            selected_variant = v
            break

    # Check overall traffic allocation (e.g. 50% of users get experiment at all)
    if bucket > experiment.allocation:
        raise ValueError("User not in experiment traffic allocation")

    assignment = Assignment(
        assignment_id=str(uuid.uuid4()),
        user_id=user_id,
        experiment_id=experiment_id,
        variant_id=selected_variant.variant_id,
        assigned_at=datetime.now(timezone.utc),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return AssignmentOut(
        user_id=assignment.user_id,
        experiment_id=assignment.experiment_id,
        variant_id=assignment.variant_id,
        variant_name=selected_variant.name,
        assigned_at=assignment.assigned_at,
    )
