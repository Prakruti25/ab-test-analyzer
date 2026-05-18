"""
Frequentist statistical tests for A/B test analysis.

Covers two of the most common cases in product experimentation:
1. Conversion rate tests (binary outcome: did the user convert?)
   -> Two-proportion z-test, with confidence intervals.
2. Continuous metric tests (e.g. revenue per user, session duration)
   -> Welch's t-test (handles unequal variances).
"""

from dataclasses import dataclass
from math import sqrt
from typing import Optional

import numpy as np
from scipy import stats


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------
@dataclass
class ProportionTestResult:
    """Holds the output of a two-proportion z-test."""
    control_rate: float
    variant_rate: float
    absolute_lift: float        # variant_rate - control_rate
    relative_lift: float        # absolute_lift / control_rate
    p_value: float
    z_statistic: float
    ci_low: float               # 95% CI on the absolute lift
    ci_high: float
    significant: bool


@dataclass
class MeanTestResult:
    """Holds the output of a Welch's t-test on a continuous metric."""
    control_mean: float
    variant_mean: float
    absolute_lift: float
    relative_lift: float
    p_value: float
    t_statistic: float
    df: float
    ci_low: float
    ci_high: float
    significant: bool


# ---------------------------------------------------------------------------
# Conversion rate test (binary outcome)
# ---------------------------------------------------------------------------
def two_proportion_z_test(
    control_conversions: int,
    control_total: int,
    variant_conversions: int,
    variant_total: int,
    alpha: float = 0.05,
) -> ProportionTestResult:
    """
    Compare conversion rates between control and variant.

    Args:
        control_conversions: # of conversions in control group
        control_total: total users in control group
        variant_conversions: # of conversions in variant group
        variant_total: total users in variant group
        alpha: significance threshold (default 0.05 = 95% confidence)

    Returns:
        ProportionTestResult with rates, lift, p-value, CI, and significance flag.
    """
    if control_total == 0 or variant_total == 0:
        raise ValueError("Both groups must have at least one user.")

    p_c = control_conversions / control_total
    p_v = variant_conversions / variant_total

    # Pooled proportion (used for the z-statistic under H0: p_c == p_v)
    pooled = (control_conversions + variant_conversions) / (control_total + variant_total)
    se_pooled = sqrt(pooled * (1 - pooled) * (1 / control_total + 1 / variant_total))

    # Avoid divide-by-zero when both rates are 0 (or both 1)
    z_stat = 0.0 if se_pooled == 0 else (p_v - p_c) / se_pooled
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    # Unpooled SE for the confidence interval on the difference
    se_unpooled = sqrt(p_c * (1 - p_c) / control_total + p_v * (1 - p_v) / variant_total)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    margin = z_crit * se_unpooled
    diff = p_v - p_c

    return ProportionTestResult(
        control_rate=p_c,
        variant_rate=p_v,
        absolute_lift=diff,
        relative_lift=diff / p_c if p_c > 0 else float("nan"),
        p_value=p_value,
        z_statistic=z_stat,
        ci_low=diff - margin,
        ci_high=diff + margin,
        significant=bool(p_value < alpha),
    )


# ---------------------------------------------------------------------------
# Continuous metric test (e.g. revenue, session length)
# ---------------------------------------------------------------------------
def welch_t_test(
    control_values: np.ndarray,
    variant_values: np.ndarray,
    alpha: float = 0.05,
) -> MeanTestResult:
    """
    Welch's t-test for comparing means of a continuous metric. Used when
    variances of the two groups may be unequal (almost always the safer default).

    Args:
        control_values: 1-D array of metric values for control users
        variant_values: 1-D array of metric values for variant users
        alpha: significance threshold

    Returns:
        MeanTestResult with means, lift, p-value, df, CI, and significance flag.
    """
    control_values = np.asarray(control_values, dtype=float)
    variant_values = np.asarray(variant_values, dtype=float)

    n_c, n_v = len(control_values), len(variant_values)
    if n_c < 2 or n_v < 2:
        raise ValueError("Each group needs at least 2 observations.")

    mean_c, mean_v = control_values.mean(), variant_values.mean()
    var_c, var_v = control_values.var(ddof=1), variant_values.var(ddof=1)

    # Welch's t-statistic and Welch–Satterthwaite degrees of freedom
    se = sqrt(var_c / n_c + var_v / n_v)
    t_stat = 0.0 if se == 0 else (mean_v - mean_c) / se
    df_num = (var_c / n_c + var_v / n_v) ** 2
    df_den = (var_c**2) / (n_c**2 * (n_c - 1)) + (var_v**2) / (n_v**2 * (n_v - 1))
    df = df_num / df_den if df_den > 0 else float("inf")

    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=df))

    t_crit = stats.t.ppf(1 - alpha / 2, df=df)
    margin = t_crit * se
    diff = mean_v - mean_c

    return MeanTestResult(
        control_mean=mean_c,
        variant_mean=mean_v,
        absolute_lift=diff,
        relative_lift=diff / mean_c if mean_c != 0 else float("nan"),
        p_value=p_value,
        t_statistic=t_stat,
        df=df,
        ci_low=diff - margin,
        ci_high=diff + margin,
        significant=bool(p_value < alpha),
    )