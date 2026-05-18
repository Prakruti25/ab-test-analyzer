"""
Statistical power analysis for A/B tests.

Two main functions:
1. required_sample_size(): How many users do I need per arm to detect a given lift?
2. observed_power(): For a completed test, what was the actual power?
"""

from math import ceil, sqrt
from scipy import stats


def required_sample_size(
    baseline_rate: float,
    minimum_detectable_effect: float,
    alpha: float = 0.05,
    power: float = 0.80,
    two_sided: bool = True,
) -> int:
    """
    Sample size needed *per arm* to detect a given relative lift in conversion rate.

    Args:
        baseline_rate: current conversion rate, e.g. 0.10 for 10%
        minimum_detectable_effect: smallest relative lift you want to detect, e.g. 0.05 for +5%
        alpha: significance threshold (default 0.05)
        power: desired statistical power (default 0.80)
        two_sided: True for two-sided test (almost always what you want)

    Returns:
        Required users per group (rounded up).
    """
    if not 0 < baseline_rate < 1:
        raise ValueError("baseline_rate must be between 0 and 1.")

    p1 = baseline_rate
    p2 = baseline_rate * (1 + minimum_detectable_effect)
    if not 0 < p2 < 1:
        raise ValueError("Resulting variant rate is outside [0, 1]. Lower the MDE.")

    z_alpha = stats.norm.ppf(1 - alpha / 2) if two_sided else stats.norm.ppf(1 - alpha)
    z_beta = stats.norm.ppf(power)

    pooled_p = (p1 + p2) / 2
    pooled_var = 2 * pooled_p * (1 - pooled_p)
    var_per_group = p1 * (1 - p1) + p2 * (1 - p2)

    n = ((z_alpha * sqrt(pooled_var) + z_beta * sqrt(var_per_group)) ** 2) / (p2 - p1) ** 2
    return ceil(n)


def observed_power(
    control_total: int,
    variant_total: int,
    control_rate: float,
    variant_rate: float,
    alpha: float = 0.05,
) -> float:
    """
    Power that the test actually had, given the observed sample sizes and rates.

    Useful for explaining a non-significant result:
        "We didn't detect a lift, but our test only had 35% power — basically a coin flip."
    """
    if control_total == 0 or variant_total == 0:
        return 0.0

    pooled_p = (control_rate * control_total + variant_rate * variant_total) / (control_total + variant_total)
    se_pooled = sqrt(pooled_p * (1 - pooled_p) * (1 / control_total + 1 / variant_total))
    se_unpooled = sqrt(
        control_rate * (1 - control_rate) / control_total
        + variant_rate * (1 - variant_rate) / variant_total
    )

    if se_unpooled == 0:
        return 1.0 if variant_rate != control_rate else 0.0

    z_crit = stats.norm.ppf(1 - alpha / 2)
    effect = abs(variant_rate - control_rate)
    z_threshold = (z_crit * se_pooled - effect) / se_unpooled
    return float(1 - stats.norm.cdf(z_threshold))