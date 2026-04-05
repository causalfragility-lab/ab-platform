"""
Seed demo data directly into the SQLite database.
Run: python demo_data/seed.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid, random
import numpy as np
from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal, engine
from app.db.models import Base, Experiment, Variant, Assignment, Event

Base.metadata.create_all(bind=engine)

random.seed(42)
np.random.seed(42)

N_USERS = 800
CONTROL_CVR   = 0.08
TREATMENT_CVR = 0.113
CONTROL_TIME   = 45.0
TREATMENT_TIME = 63.0


def seed():
    db = SessionLocal()
    try:
        for m in [Event, Assignment, Variant, Experiment]:
            db.query(m).delete()
        db.commit()

        print("── Creating experiment...")
        exp_id = "exp_demo_001"
        exp = Experiment(
            experiment_id=exp_id,
            name="Email Campaign Landing Page Test",
            description="Tests new landing page design for email campaign signups.",
            metric_name="conversion",
            metric_type="binary",
            allocation=1.0,
            status="running",
            start_date=datetime.now(timezone.utc) - timedelta(days=14),
        )
        db.add(exp)
        db.flush()

        ctrl_id = "var_control_001"
        trt_id  = "var_treatment_001"
        db.add(Variant(variant_id=ctrl_id, experiment_id=exp_id, name="control",   allocation_weight=0.5))
        db.add(Variant(variant_id=trt_id,  experiment_id=exp_id, name="treatment", allocation_weight=0.5))
        db.flush()
        print(f"   Experiment ID: {exp_id}")

        print("── Seeding users, assignments, events...")
        from app.core.hashing import deterministic_hash

        start = datetime.now(timezone.utc) - timedelta(days=14)
        ctrl_vals, trt_vals = [], []

        for i in range(N_USERS):
            user_id = f"user_{i:05d}"
            bucket  = deterministic_hash(user_id, exp_id)
            var_id  = ctrl_id if bucket < 0.5 else trt_id
            is_ctrl = var_id == ctrl_id

            event_time = start + timedelta(
                days=random.randint(0, 13),
                seconds=random.randint(0, 86400)
            )

            db.add(Assignment(
                assignment_id=str(uuid.uuid4()),
                user_id=user_id,
                experiment_id=exp_id,
                variant_id=var_id,
                assigned_at=event_time,
            ))

            db.add(Event(
                event_id=str(uuid.uuid4()),
                user_id=user_id, experiment_id=exp_id,
                event_name="exposure", event_value=1.0, event_time=event_time,
            ))

            cvr = CONTROL_CVR if is_ctrl else TREATMENT_CVR
            converted = float(np.random.binomial(1, cvr))
            db.add(Event(
                event_id=str(uuid.uuid4()),
                user_id=user_id, experiment_id=exp_id,
                event_name="conversion", event_value=converted,
                event_time=event_time + timedelta(seconds=random.randint(10, 300)),
            ))
            (ctrl_vals if is_ctrl else trt_vals).append(converted)

            base = CONTROL_TIME if is_ctrl else TREATMENT_TIME
            time_val = max(5.0, float(np.random.normal(base, 15)))
            db.add(Event(
                event_id=str(uuid.uuid4()),
                user_id=user_id, experiment_id=exp_id,
                event_name="time_on_page", event_value=round(time_val, 1),
                event_time=event_time,
            ))

        db.commit()
        print(f"   Control: {len(ctrl_vals)} | Treatment: {len(trt_vals)}")

        from app.core.inference import binary_test, sample_ratio_mismatch, fragility_warning
        stats = binary_test(ctrl_vals, trt_vals)
        srm, srm_p = sample_ratio_mismatch(len(ctrl_vals), len(trt_vals))
        frag = fragility_warning(stats["p_value"], stats["lift_absolute"], stats["ci_lower"], stats["ci_upper"])

        print(f"""
Results:
  Control CVR : {stats['control_mean']:.4f}  (n={stats['control_n']})
  Treatment   : {stats['treatment_mean']:.4f}  (n={stats['treatment_n']})
  Lift        : {stats['lift_relative']*100:+.2f}%
  p-value     : {stats['p_value']:.4f}
  95% CI      : [{stats['ci_lower']:.4f}, {stats['ci_upper']:.4f}]
  Significant : {stats['statistically_significant']}
  SRM         : {srm} (p={srm_p:.4f})
  Fragility   : {frag or 'None'}
Experiment ID : {exp_id}
        """)

    finally:
        db.close()


if __name__ == "__main__":
    seed()
