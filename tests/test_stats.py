"""
Unit tests for the stats engine. Run with: pytest tests/
"""

import numpy as np
import pytest

from src.frequentist import two_proportion_z_test, welch_t_test
from src.power import required_sample_size, observed_power


# ---------------------------------------------------------------------------
# Two-proportion z-test
# ---------------------------------------------------------------------------
class TestProportionTest:
    def test_no_lift_returns_zero_diff(self):
        r = two_proportion_z_test(100, 1000, 100, 1000)
        assert r.absolute_lift == 0.0
        assert r.p_value > 0.9      # nothing happened, p should be near 1
        assert r.significant is False

    def test_clear_winner_detected(self):
        # Variant clearly better: 8% vs 12% on 10K samples each
        r = two_proportion_z_test(800, 10_000, 1200, 10_000)
        assert r.variant_rate > r.control_rate
        assert r.p_value < 0.001
        assert r.significant is True
        # CI for the lift should be entirely positive
        assert r.ci_low > 0

    def test_relative_lift_calculation(self):
        # 10% -> 11% is a +10% relative lift
        r = two_proportion_z_test(100, 1000, 110, 1000)
        assert r.relative_lift == pytest.approx(0.10, abs=0.01)

    def test_raises_on_zero_total(self):
        with pytest.raises(ValueError):
            two_proportion_z_test(0, 0, 1, 100)


# ---------------------------------------------------------------------------
# Welch's t-test
# ---------------------------------------------------------------------------
class TestWelchTTest:
    def test_identical_samples(self):
        rng = np.random.default_rng(42)
        x = rng.normal(50, 10, size=500)
        r = welch_t_test(x, x.copy())
        assert r.absolute_lift == 0.0
        assert r.p_value > 0.99

    def test_detects_real_difference(self):
        rng = np.random.default_rng(0)
        c = rng.normal(100, 20, size=1000)
        v = rng.normal(110, 20, size=1000)  # +10 unit lift
        r = welch_t_test(c, v)
        assert r.variant_mean > r.control_mean
        assert r.p_value < 0.001
        assert r.significant is True

    def test_raises_on_too_few_observations(self):
        with pytest.raises(ValueError):
            welch_t_test([1.0], [2.0])


# ---------------------------------------------------------------------------
# Power analysis
# ---------------------------------------------------------------------------
class TestPower:
    def test_smaller_mde_needs_more_users(self):
        big_n = required_sample_size(baseline_rate=0.10, minimum_detectable_effect=0.02)
        small_n = required_sample_size(baseline_rate=0.10, minimum_detectable_effect=0.20)
        assert big_n > small_n

    def test_underpowered_test_returns_low_power(self):
        # Tiny sample, small effect → power should be low
        p = observed_power(100, 100, 0.10, 0.11)
        assert 0 <= p < 0.30

    def test_well_powered_test_returns_high_power(self):
        # Big sample, clear effect → power should be high
        p = observed_power(10_000, 10_000, 0.10, 0.13)
        assert p > 0.95

# ---------------------------------------------------------------------------
# Bayesian conversion test
# ---------------------------------------------------------------------------
from src.bayesian import bayesian_conversion_test, interpret_bayesian_result


class TestBayesian:
    def test_clear_winner_high_probability(self):
        # 8% vs 12% on 10K each — variant should win with high probability
        r = bayesian_conversion_test(800, 10_000, 1200, 10_000)
        assert r.prob_variant_better > 0.99
        assert r.expected_lift > 0
        # Credible interval shouldn't cross zero
        assert r.credible_interval_low > 0

    def test_no_difference_uncertain(self):
        # Same rate on both arms — should be near 50/50
        r = bayesian_conversion_test(100, 1000, 100, 1000)
        assert 0.35 < r.prob_variant_better < 0.65

    def test_variant_clearly_worse(self):
        # Variant is worse: 12% vs 8%
        r = bayesian_conversion_test(1200, 10_000, 800, 10_000)
        assert r.prob_variant_better < 0.01
        assert r.expected_lift < 0

    def test_interpretation_returns_string(self):
        r = bayesian_conversion_test(800, 10_000, 1200, 10_000)
        msg = interpret_bayesian_result(r)
        assert isinstance(msg, str)
        assert "%" in msg

    def test_raises_on_zero_users(self):
        with pytest.raises(ValueError):
            bayesian_conversion_test(0, 0, 1, 100)