from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.models import Experiment, Assignment, Event, Variant
from app.core import inference as inf
from app.core.diagnostics import missing_data_flags


def compute_results(db: Session, experiment_id: str) -> Dict[str, Any]:
    experiment = db.query(Experiment).filter(Experiment.experiment_id == experiment_id).first()
    if not experiment:
        raise ValueError(f"Experiment {experiment_id} not found")

    variants = {v.variant_id: v.name for v in experiment.variants}
    if len(variants) < 2:
        raise ValueError("Need at least 2 variants")

    variant_ids = list(variants.keys())
    control_id = variant_ids[0]
    treatment_id = variant_ids[1]

    # Assignments per variant
    assignments = db.query(Assignment).filter(Assignment.experiment_id == experiment_id).all()
    control_users = {a.user_id for a in assignments if a.variant_id == control_id}
    treatment_users = {a.user_id for a in assignments if a.variant_id == treatment_id}

    # Events — filter to exposed users with outcome
    events = db.query(Event).filter(
        Event.experiment_id == experiment_id,
        Event.event_name == experiment.metric_name,
    ).all()

    def get_values(users):
        vals = []
        for e in events:
            if e.user_id in users:
                if experiment.metric_type == "binary":
                    vals.append(1.0 if e.event_value else 0.0)
                else:
                    vals.append(float(e.event_value) if e.event_value is not None else 0.0)
        return vals

    control_vals = get_values(control_users)
    treatment_vals = get_values(treatment_users)

    if len(control_vals) < 2 or len(treatment_vals) < 2:
        raise ValueError("Not enough outcome data to compute results")

    # Run inference
    if experiment.metric_type == "binary":
        stats_result = inf.binary_test(control_vals, treatment_vals)
    else:
        stats_result = inf.continuous_test(control_vals, treatment_vals)

    # SRM check — expected ratio from variant weights
    control_variant = db.query(Variant).filter(Variant.variant_id == control_id).first()
    expected_ratio = control_variant.allocation_weight if control_variant else 0.5
    srm_flag, srm_p = inf.sample_ratio_mismatch(
        len(control_users), len(treatment_users), expected_ratio=expected_ratio
    )

    # Fragility warning
    fragility = inf.fragility_warning(
        stats_result["p_value"],
        stats_result["lift_absolute"],
        stats_result["ci_lower"],
        stats_result["ci_upper"],
    )

    # Missing data
    dropout_info = missing_data_flags(
        len(control_vals), len(treatment_vals),
        len(control_users), len(treatment_users)
    )

    # Build interpretation string
    sig = stats_result["statistically_significant"]
    lift_pct = stats_result["lift_relative"] * 100
    interpretation = (
        f"Treatment {'increased' if lift_pct >= 0 else 'decreased'} "
        f"{experiment.metric_name} by {abs(lift_pct):.1f}% "
        f"({'statistically significant' if sig else 'not significant'} at α=0.05)."
    )
    if fragility:
        interpretation += f" ⚠ {fragility}"

    # Daily trends (dates from events)
    control_events = [(e.event_time.date().isoformat(), float(e.event_value or 0))
                      for e in events if e.user_id in control_users]
    treatment_events = [(e.event_time.date().isoformat(), float(e.event_value or 0))
                        for e in events if e.user_id in treatment_users]

    import pandas as pd
    import numpy as np

    def daily_means(event_tuples):
        if not event_tuples:
            return {}
        df = pd.DataFrame(event_tuples, columns=["date", "value"])
        return df.groupby("date")["value"].mean().to_dict()

    dc = daily_means(control_events)
    dt = daily_means(treatment_events)
    all_dates = sorted(set(dc) | set(dt))
    daily_trends = [
        {"date": d, "control": round(dc.get(d, float("nan")), 4), "treatment": round(dt.get(d, float("nan")), 4)}
        for d in all_dates
    ]

    return {
        "experiment_id": experiment_id,
        "experiment_name": experiment.name,
        "metric_name": experiment.metric_name,
        "metric_type": experiment.metric_type,
        "control": {
            "variant_id": control_id,
            "variant_name": variants[control_id],
            "n": len(control_vals),
            "mean": stats_result["control_mean"],
            "std": stats_result["control_std"],
        },
        "treatment": {
            "variant_id": treatment_id,
            "variant_name": variants[treatment_id],
            "n": len(treatment_vals),
            "mean": stats_result["treatment_mean"],
            "std": stats_result["treatment_std"],
        },
        "lift_absolute": stats_result["lift_absolute"],
        "lift_relative": stats_result["lift_relative"],
        "p_value": stats_result["p_value"],
        "ci_lower": stats_result["ci_lower"],
        "ci_upper": stats_result["ci_upper"],
        "statistically_significant": stats_result["statistically_significant"],
        "practically_significant": abs(stats_result["lift_relative"]) > 0.01,
        "interpretation": interpretation,
        "sample_ratio_mismatch": srm_flag,
        "srm_p_value": srm_p,
        "dropout_info": dropout_info,
        "fragility_warning": fragility,
        "daily_trends": daily_trends,
    }
