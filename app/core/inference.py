import numpy as np
from scipy import stats
from typing import List, Tuple, Optional, Dict


# ─────────────────────────────────────────────
# Core estimators
# ─────────────────────────────────────────────

def binary_test(control_values: List[float], treatment_values: List[float], alpha: float = 0.05) -> dict:
    """Two-proportion z-test for binary (0/1) outcomes."""
    n_c, n_t = len(control_values), len(treatment_values)
    p_c = np.mean(control_values)
    p_t = np.mean(treatment_values)

    pooled = (p_c * n_c + p_t * n_t) / (n_c + n_t)
    se_pooled = np.sqrt(pooled * (1 - pooled) * (1 / n_c + 1 / n_t))

    if se_pooled == 0:
        return _empty_result(p_c, p_t, n_c, n_t)

    z = (p_t - p_c) / se_pooled
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    # CI on the difference using unpooled SE
    se_diff = np.sqrt(p_c * (1 - p_c) / n_c + p_t * (1 - p_t) / n_t)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_lower = (p_t - p_c) - z_crit * se_diff
    ci_upper = (p_t - p_c) + z_crit * se_diff

    return _build_result(p_c, p_t, n_c, n_t, p_value, ci_lower, ci_upper, alpha,
                         std_c=np.std(control_values, ddof=1),
                         std_t=np.std(treatment_values, ddof=1))


def continuous_test(control_values: List[float], treatment_values: List[float], alpha: float = 0.05) -> dict:
    """Welch's t-test for continuous outcomes."""
    n_c, n_t = len(control_values), len(treatment_values)
    m_c, m_t = np.mean(control_values), np.mean(treatment_values)
    s_c, s_t = np.std(control_values, ddof=1), np.std(treatment_values, ddof=1)

    if n_c < 2 or n_t < 2:
        return _empty_result(m_c, m_t, n_c, n_t)

    t_stat, p_value = stats.ttest_ind(treatment_values, control_values, equal_var=False)

    # Welch CI
    se = np.sqrt(s_c**2 / n_c + s_t**2 / n_t)
    df = _welch_df(s_c, s_t, n_c, n_t)
    t_crit = stats.t.ppf(1 - alpha / 2, df=df)
    ci_lower = (m_t - m_c) - t_crit * se
    ci_upper = (m_t - m_c) + t_crit * se

    return _build_result(m_c, m_t, n_c, n_t, p_value, ci_lower, ci_upper, alpha,
                         std_c=s_c, std_t=s_t)


# ─────────────────────────────────────────────
# Sample Ratio Mismatch (SRM) check
# ─────────────────────────────────────────────

def sample_ratio_mismatch(n_control: int, n_treatment: int, expected_ratio: float = 0.5, alpha: float = 0.01) -> Tuple[bool, float]:
    """
    Chi-square test for SRM.
    expected_ratio: expected fraction in control arm (e.g. 0.5 for 50/50 split).
    Returns (srm_detected, p_value).
    """
    total = n_control + n_treatment
    expected_c = total * expected_ratio
    expected_t = total * (1 - expected_ratio)

    if expected_c == 0 or expected_t == 0:
        return False, 1.0

    chi2 = (n_control - expected_c)**2 / expected_c + (n_treatment - expected_t)**2 / expected_t
    p_value = 1 - stats.chi2.cdf(chi2, df=1)
    return bool(p_value < alpha), float(p_value)


# ─────────────────────────────────────────────
# Robustness checks
# ─────────────────────────────────────────────

def compute_daily_trends(dates, control_values, treatment_values) -> Dict:
    """
    Compute cumulative running lift by day to detect drift or peeking effects.
    dates: list of date strings (one per observation, aligned with values)
    """
    import pandas as pd

    df_c = pd.DataFrame({"date": dates[0], "value": control_values})
    df_t = pd.DataFrame({"date": dates[1], "value": treatment_values})

    df_c["date"] = pd.to_datetime(df_c["date"])
    df_t["date"] = pd.to_datetime(df_t["date"])

    daily_c = df_c.groupby("date")["value"].mean()
    daily_t = df_t.groupby("date")["value"].mean()

    all_dates = sorted(set(daily_c.index) | set(daily_t.index))
    trends = []
    for d in all_dates:
        trends.append({
            "date": str(d.date()),
            "control_mean": round(float(daily_c.get(d, np.nan)), 4),
            "treatment_mean": round(float(daily_t.get(d, np.nan)), 4),
        })

    return {"daily": trends}


def fragility_warning(p_value: float, lift_absolute: float, ci_lower: float, ci_upper: float) -> Optional[str]:
    """
    Flags results that are statistically significant but practically fragile.
    """
    warnings = []
    if p_value < 0.05 and ci_lower < 0 < ci_upper:
        warnings.append("CI crosses zero — result is borderline.")
    if p_value < 0.05 and abs(lift_absolute) < 0.005:
        warnings.append("Effect size is very small; may lack practical significance.")
    if 0.04 < p_value < 0.05:
        warnings.append("p-value is near threshold — treat result with caution.")
    return " | ".join(warnings) if warnings else None


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _welch_df(s_c, s_t, n_c, n_t):
    num = (s_c**2 / n_c + s_t**2 / n_t)**2
    den = (s_c**2 / n_c)**2 / (n_c - 1) + (s_t**2 / n_t)**2 / (n_t - 1)
    return num / den if den > 0 else n_c + n_t - 2


def _build_result(m_c, m_t, n_c, n_t, p_value, ci_lower, ci_upper, alpha,
                  std_c=0.0, std_t=0.0) -> dict:
    lift_abs = m_t - m_c
    lift_rel = (lift_abs / m_c) if m_c != 0 else 0.0
    return {
        "control_mean": float(m_c),
        "treatment_mean": float(m_t),
        "control_n": int(n_c),
        "treatment_n": int(n_t),
        "control_std": float(std_c),
        "treatment_std": float(std_t),
        "lift_absolute": float(lift_abs),
        "lift_relative": float(lift_rel),
        "p_value": float(p_value),
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "statistically_significant": bool(p_value < alpha),
    }


def _empty_result(m_c, m_t, n_c, n_t) -> dict:
    return {
        "control_mean": float(m_c),
        "treatment_mean": float(m_t),
        "control_n": int(n_c),
        "treatment_n": int(n_t),
        "control_std": 0.0,
        "treatment_std": 0.0,
        "lift_absolute": float(m_t - m_c),
        "lift_relative": 0.0,
        "p_value": 1.0,
        "ci_lower": 0.0,
        "ci_upper": 0.0,
        "statistically_significant": False,
    }