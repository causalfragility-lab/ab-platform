from typing import List, Dict, Optional
import numpy as np
from scipy import stats


def check_balance(control_values: List[float], treatment_values: List[float]) -> Dict:
    """
    Checks if pre-experiment covariates are balanced across arms.
    Uses a simple t-test on any numeric covariate passed in.
    Returns imbalance score and flag.
    """
    if not control_values or not treatment_values:
        return {"balanced": True, "p_value": None, "note": "No covariate data"}

    _, p = stats.ttest_ind(control_values, treatment_values, equal_var=False)
    balanced = p > 0.05
    return {
        "balanced": balanced,
        "p_value": round(float(p), 4),
        "note": "Imbalance detected — consider covariate adjustment." if not balanced else "Arms appear balanced.",
    }


def missing_data_flags(control_n: int, treatment_n: int, total_assigned_control: int, total_assigned_treatment: int) -> Dict:
    """
    Checks if a substantial fraction of assigned users have no outcome events.
    """
    if total_assigned_control == 0 or total_assigned_treatment == 0:
        return {"flag": False, "note": "No assignments yet."}

    dropout_c = 1 - control_n / total_assigned_control
    dropout_t = 1 - treatment_n / total_assigned_treatment

    flag = dropout_c > 0.3 or dropout_t > 0.3
    return {
        "flag": flag,
        "control_dropout_rate": round(dropout_c, 4),
        "treatment_dropout_rate": round(dropout_t, 4),
        "note": "High dropout rate detected — results may be biased." if flag else "Dropout rates look acceptable.",
    }
