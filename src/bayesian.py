"""
Bayesian analysis for A/B tests using the Beta-Binomial model.

Why this matters: frequentist tests give you a p-value, which is hard to
explain to non-technical stakeholders. Bayesian gives you the probability
the variant is better — exactly what a PM wants to hear.
"""

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class BayesianResult:
    """Holds the output of a Bayesian conversion-rate comparison."""
    prob_variant_better: float          # P(variant > control)
    prob_variant_meaningfully_better: float  # P(variant > control by >= threshold)
    expected_lift: float                # mean of (variant - control) posterior
    credible_interval_low: float        # 95% credible interval on the lift
    credible_interval_high: float
    expected_loss_choosing_variant: float   # avg downside if we pick variant
    expected_loss_choosing_control: float   # avg downside if we stick with control


def bayesian_conversion_test(
    control_conversions: int,
    control_total: int,
    variant_conversions: int,
    variant_total: int,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    meaningful_lift_threshold: float = 0.0,
    n_samples: int = 100_000,
    random_state: int = 42,
) -> BayesianResult:
    """
    Bayesian comparison of two conversion rates using Beta-Binomial conjugacy.

    Args:
        control_conversions: # conversions in control
        control_total:       # users in control
        variant_conversions: # conversions in variant
        variant_total:       # users in variant
        prior_alpha, prior_beta: Beta prior parameters. (1, 1) = uniform = no opinion.
        meaningful_lift_threshold: a relative lift below which we say "meh, not worth it."
                                   e.g. 0.01 means "variant is meaningfully better only
                                   if it's at least 1% higher than control."
        n_samples: how many posterior samples to draw (more = smoother)
        random_state: for reproducibility

    Returns:
        BayesianResult with all the probabilities and credible intervals.
    """
    if control_total < 1 or variant_total < 1:
        raise ValueError("Both groups must have at least one user.")

    rng = np.random.default_rng(random_state)

    # Posteriors are Beta distributions
    control_posterior = stats.beta(
        prior_alpha + control_conversions,
        prior_beta + (control_total - control_conversions),
    )
    variant_posterior = stats.beta(
        prior_alpha + variant_conversions,
        prior_beta + (variant_total - variant_conversions),
    )

    # Monte Carlo: sample from each posterior, compare
    control_samples = control_posterior.rvs(n_samples, random_state=rng)
    variant_samples = variant_posterior.rvs(n_samples, random_state=rng)

    lift_samples = variant_samples - control_samples
    prob_better = float((variant_samples > control_samples).mean())

    # "Meaningfully better" = variant beats control by at least threshold (relative)
    if meaningful_lift_threshold > 0:
        meaningful_threshold_abs = control_samples * meaningful_lift_threshold
        prob_meaningful = float((lift_samples > meaningful_threshold_abs).mean())
    else:
        prob_meaningful = prob_better

    # Expected loss: if we pick variant, how much do we lose IN THE WORLDS WHERE WE'RE WRONG?
    # (This is the risk-adjusted metric used by serious experimentation teams.)
    loss_if_variant = float(np.maximum(control_samples - variant_samples, 0).mean())
    loss_if_control = float(np.maximum(variant_samples - control_samples, 0).mean())

    return BayesianResult(
        prob_variant_better=prob_better,
        prob_variant_meaningfully_better=prob_meaningful,
        expected_lift=float(lift_samples.mean()),
        credible_interval_low=float(np.percentile(lift_samples, 2.5)),
        credible_interval_high=float(np.percentile(lift_samples, 97.5)),
        expected_loss_choosing_variant=loss_if_variant,
        expected_loss_choosing_control=loss_if_control,
    )


def interpret_bayesian_result(result: BayesianResult) -> str:
    """Return a plain-English interpretation of a Bayesian result."""
    p = result.prob_variant_better
    if p >= 0.95:
        verdict = "Strong evidence the variant is better."
    elif p >= 0.85:
        verdict = "Moderate evidence the variant is better."
    elif p >= 0.55:
        verdict = "Weak evidence the variant is better — keep testing."
    elif p <= 0.05:
        verdict = "Strong evidence the variant is worse."
    elif p <= 0.15:
        verdict = "Moderate evidence the variant is worse."
    else:
        verdict = "Inconclusive — variant and control look similar."

    return (
        f"{verdict} "
        f"Variant has a {p*100:.1f}% chance of beating control. "
        f"Expected lift: {result.expected_lift*100:+.2f} percentage points "
        f"(95% credible interval: {result.credible_interval_low*100:+.2f} to "
        f"{result.credible_interval_high*100:+.2f})."
    )