"""
A/B Test Analyzer — Streamlit UI.

Lets a user enter conversion-rate test data and get a complete statistical
report: frequentist, Bayesian, and power analysis, all with plain-English
interpretation.
"""

import sys
from pathlib import Path

# Make `src/` importable when streamlit runs this from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

from src.bayesian import bayesian_conversion_test, interpret_bayesian_result
from src.frequentist import two_proportion_z_test
from src.power import observed_power, required_sample_size


# === PAGE CONFIG ===
st.set_page_config(
    page_title="A/B Test Analyzer",
    page_icon="🧪",
    layout="wide",
)


# === SIDEBAR: CONTROLS & SAMPLE-SIZE CALCULATOR ===
with st.sidebar:
    st.header("⚙️ Settings")
    alpha = st.slider("Significance level (α)", 0.01, 0.10, 0.05, 0.01)
    meaningful_lift = st.slider(
        "Meaningful relative lift threshold (%)",
        0.0, 10.0, 1.0, 0.5,
        help="The smallest relative lift you'd care about in practice.",
    ) / 100

    st.divider()
    st.subheader("📏 Sample-size calculator")
    st.caption("How many users per arm do I need?")
    baseline = st.number_input("Baseline conversion rate (%)", 0.1, 99.0, 10.0, 0.1) / 100
    mde = st.number_input("Min. relative effect to detect (%)", 0.5, 100.0, 5.0, 0.5) / 100
    power_target = st.slider("Desired power", 0.70, 0.99, 0.80, 0.01)

    try:
        n_required = required_sample_size(baseline, mde, alpha=alpha, power=power_target)
        st.metric("Users needed per arm", f"{n_required:,}")
    except ValueError as e:
        st.error(str(e))

    st.divider()
    st.caption("Built with Python, scipy, statsmodels, and Streamlit.")


# === HEADER ===
st.title("🧪 A/B Test Analyzer")
st.markdown(
    "A rigorous statistical analyzer for A/B test results — **frequentist + "
    "Bayesian + power analysis** with plain-English interpretation."
)


# === DATA INPUT ===
st.subheader("📊 Enter your test results")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Control (A)**")
    control_users = st.number_input("Users (control)", 1, 10_000_000, 1000, key="cu")
    control_conv = st.number_input("Conversions (control)", 0, 10_000_000, 80, key="cc")
with col2:
    st.markdown("**Variant (B)**")
    variant_users = st.number_input("Users (variant)", 1, 10_000_000, 1000, key="vu")
    variant_conv = st.number_input("Conversions (variant)", 0, 10_000_000, 95, key="vc")

if control_conv > control_users or variant_conv > variant_users:
    st.error("Conversions can't exceed users.")
    st.stop()


# === RUN THE STATS ===
freq = two_proportion_z_test(control_conv, control_users, variant_conv, variant_users, alpha=alpha)
bayes = bayesian_conversion_test(
    control_conv, control_users, variant_conv, variant_users,
    meaningful_lift_threshold=meaningful_lift,
)
power = observed_power(control_users, variant_users, freq.control_rate, freq.variant_rate, alpha=alpha)


# === HEADLINE METRICS ===
st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Control rate",  f"{freq.control_rate*100:.2f}%")
c2.metric("Variant rate",  f"{freq.variant_rate*100:.2f}%",
          delta=f"{freq.absolute_lift*100:+.2f} pp")
c3.metric("Relative lift", f"{freq.relative_lift*100:+.1f}%")
c4.metric("P(variant > control)",
          f"{bayes.prob_variant_better*100:.1f}%",
          delta="Bayesian")


# === VERDICT BOX ===
st.divider()
verdict = interpret_bayesian_result(bayes)
if bayes.prob_variant_better >= 0.95:
    st.success(f"✅ **Ship the variant.** {verdict}")
elif bayes.prob_variant_better >= 0.85:
    st.info(f"🟡 **Lean variant — but consider more data.** {verdict}")
elif bayes.prob_variant_better <= 0.05:
    st.error(f"🛑 **Do not ship.** {verdict}")
elif bayes.prob_variant_better <= 0.15:
    st.warning(f"🔻 **Lean against variant.** {verdict}")
else:
    st.warning(f"⚖️ **Inconclusive.** {verdict}")


# === DETAILED TABS ===
tab1, tab2, tab3 = st.tabs(["📈 Frequentist", "🎲 Bayesian", "⚡ Power"])

with tab1:
    st.markdown("**Two-proportion z-test results**")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("p-value", f"{freq.p_value:.4f}")
    col_b.metric("z-statistic", f"{freq.z_statistic:.3f}")
    col_c.metric("Significant?", "Yes ✅" if freq.significant else "No ❌")
    st.markdown(
        f"**95% confidence interval on absolute lift:** "
        f"`[{freq.ci_low*100:+.2f}, {freq.ci_high*100:+.2f}]` percentage points"
    )
    st.caption(
        "p-value tells us how unusual our observed lift would be if there were truly no difference. "
        "A p-value below α (currently " + f"{alpha}" + ") is conventionally called 'significant'."
    )

with tab2:
    st.markdown("**Bayesian Beta-Binomial inference**")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("P(variant > control)", f"{bayes.prob_variant_better*100:.1f}%")
    col_b.metric(f"P(meaningfully better)", f"{bayes.prob_variant_meaningfully_better*100:.1f}%")
    col_c.metric("Expected lift", f"{bayes.expected_lift*100:+.2f} pp")
    st.markdown(
        f"**95% credible interval on lift:** "
        f"`[{bayes.credible_interval_low*100:+.2f}, {bayes.credible_interval_high*100:+.2f}]` pp"
    )
    st.markdown(
        f"**Expected loss if we pick variant:** `{bayes.expected_loss_choosing_variant*100:.3f} pp` &nbsp;&nbsp; "
        f"**vs. if we stick with control:** `{bayes.expected_loss_choosing_control*100:.3f} pp`"
    )

    # Posterior distributions chart
    x = np.linspace(0, max(freq.control_rate, freq.variant_rate) * 2 + 0.05, 500)
    control_pdf = stats.beta.pdf(x, 1 + control_conv, 1 + control_users - control_conv)
    variant_pdf = stats.beta.pdf(x, 1 + variant_conv, 1 + variant_users - variant_conv)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x*100, y=control_pdf, name="Control posterior",
                             fill="tozeroy", line=dict(color="#1f77b4")))
    fig.add_trace(go.Scatter(x=x*100, y=variant_pdf, name="Variant posterior",
                             fill="tozeroy", line=dict(color="#2ca02c"), opacity=0.7))
    fig.update_layout(
        height=350,
        xaxis_title="Conversion rate (%)",
        yaxis_title="Posterior density",
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Each curve shows the range of plausible true conversion rates for that arm, "
        "given the observed data. The more they overlap, the less certain we are."
    )

with tab3:
    st.markdown("**Power analysis**")
    col_a, col_b = st.columns(2)
    col_a.metric("Observed power", f"{power*100:.1f}%")
    if power < 0.80:
        col_b.warning("⚠️ Test was underpowered — be cautious about null results.")
    else:
        col_b.success("✅ Test was adequately powered.")
    st.caption(
        "Power = probability of detecting a real effect if one exists. "
        "Industry convention is 80%. Below that, a null result may just mean "
        "your test was too small — not that the variant didn't work."
    )


# === FOOTER ===
st.divider()
st.caption(
    "Built with Python · scipy · statsmodels · Streamlit · Plotly. "
    "Frequentist: two-proportion z-test. Bayesian: Beta-Binomial with uniform prior. "
    "All stats functions are unit-tested with pytest."
)