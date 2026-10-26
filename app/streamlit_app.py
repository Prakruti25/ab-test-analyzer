"""
Two Links, One Story — a simple A/B test analyzer.

Enter views and clicks for two links to the same story. The app tells you
which link readers prefer and whether the difference is real or just luck.
"""

import sys
from pathlib import Path

# Make `src/` importable when streamlit runs this from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

from src.bayesian import bayesian_conversion_test
from src.frequentist import two_proportion_z_test
from src.power import observed_power

# Fixed, standard settings
ALPHA = 0.05
MEANINGFUL_LIFT = 0.01

st.set_page_config(page_title="Two Links, One Story", page_icon="🔗", layout="wide")

# === DEFAULTS (so the example button can fill the inputs) ===
st.session_state.setdefault("name_a", "Headline A")
st.session_state.setdefault("name_b", "Headline B")
st.session_state.setdefault("cu", 1000)
st.session_state.setdefault("cc", 80)
st.session_state.setdefault("vu", 1000)
st.session_state.setdefault("vc", 95)


def load_example():
    st.session_state["name_a"] = "Headline A: 'City Council Approves New Budget'"
    st.session_state["name_b"] = "Headline B: 'How the New Budget Will Affect You'"
    st.session_state["cu"] = 4200
    st.session_state["cc"] = 310
    st.session_state["vu"] = 4150
    st.session_state["vc"] = 365


# === HEADER ===
st.title("🔗 Two Links, One Story")
st.markdown(
    "A newspaper publishes the **same story under two links or headlines**. "
    "Enter how many readers saw each and how many clicked. "
    "This tells you **which one readers prefer — and whether the difference is real or just luck.**"
)
st.caption(
    "Measures reader engagement, not factual accuracy. "
    "The numbers here are sample data; in real use they would come from a site's analytics."
)
st.button("📰 Load example", on_click=load_example)

# === INPUT ===
col1, col2 = st.columns(2)
with col1:
    name_a = st.text_input("Name of first link", key="name_a")
    control_users = st.number_input("Views (A)", 1, 10_000_000, key="cu")
    control_conv = st.number_input("Clicks (A)", 0, 10_000_000, key="cc")
with col2:
    name_b = st.text_input("Name of second link", key="name_b")
    variant_users = st.number_input("Views (B)", 1, 10_000_000, key="vu")
    variant_conv = st.number_input("Clicks (B)", 0, 10_000_000, key="vc")

if control_conv > control_users or variant_conv > variant_users:
    st.error("Clicks can't be higher than views.")
    st.stop()

# === STATS ===
freq = two_proportion_z_test(control_conv, control_users, variant_conv, variant_users, alpha=ALPHA)
bayes = bayesian_conversion_test(
    control_conv, control_users, variant_conv, variant_users,
    meaningful_lift_threshold=MEANINGFUL_LIFT,
)
power = observed_power(control_users, variant_users, freq.control_rate, freq.variant_rate, alpha=ALPHA)

# === RESULT ===
st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("A click rate", f"{freq.control_rate*100:.2f}%")
c2.metric("B click rate", f"{freq.variant_rate*100:.2f}%", delta=f"{freq.absolute_lift*100:+.2f} pp")
c3.metric("Chance B beats A", f"{bayes.prob_variant_better*100:.1f}%")

p_b = bayes.prob_variant_better
if freq.significant and freq.absolute_lift > 0:
    st.success(
        f"🏆 **Winner: {name_b}.** The difference is statistically significant "
        f"(p = {freq.p_value:.4f}), with a {p_b*100:.1f}% chance it truly performs better. "
        f"**Recommendation: promote this link.**"
    )
elif freq.significant and freq.absolute_lift < 0:
    st.success(
        f"🏆 **Winner: {name_a}.** The difference is statistically significant "
        f"(p = {freq.p_value:.4f}), with a {(1-p_b)*100:.1f}% chance it truly performs better. "
        f"**Recommendation: promote this link.**"
    )
else:
    leader = name_b if freq.absolute_lift > 0 else name_a
    chance = p_b if freq.absolute_lift > 0 else 1 - p_b
    st.warning(
        f"⚖️ **No clear winner yet.** {leader} is ahead ({chance*100:.1f}% chance of being better), "
        f"but the gap isn't statistically significant (p = {freq.p_value:.4f}) and could be luck. "
        f"**Recommendation: collect more data before deciding.**"
    )

# === DETAILS ===
tab1, tab2, tab3 = st.tabs(["📈 Frequentist", "🎲 Bayesian", "⚡ Power"])

with tab1:
    a, b, c = st.columns(3)
    a.metric("p-value", f"{freq.p_value:.4f}")
    b.metric("z-statistic", f"{freq.z_statistic:.3f}")
    c.metric("Significant?", "Yes ✅" if freq.significant else "No ❌")
    st.markdown(
        f"**95% confidence interval on the difference:** "
        f"`[{freq.ci_low*100:+.2f}, {freq.ci_high*100:+.2f}]` percentage points"
    )
    st.caption(
        "The p-value is how often we'd see a gap this big by pure luck if the two links "
        "were truly equal. Below 0.05 is conventionally called 'significant'."
    )

with tab2:
    a, b, c = st.columns(3)
    a.metric("Chance B beats A", f"{bayes.prob_variant_better*100:.1f}%")
    b.metric("Expected difference", f"{bayes.expected_lift*100:+.2f} pp")
    c.metric("Expected loss if we pick B", f"{bayes.expected_loss_choosing_variant*100:.3f} pp")
    st.markdown(
        f"**95% credible interval:** "
        f"`[{bayes.credible_interval_low*100:+.2f}, {bayes.credible_interval_high*100:+.2f}]` pp"
    )
    x = np.linspace(0, max(freq.control_rate, freq.variant_rate) * 2 + 0.05, 500)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x*100, y=stats.beta.pdf(x, 1 + control_conv, 1 + control_users - control_conv),
                             name="A", fill="tozeroy", line=dict(color="#1f77b4")))
    fig.add_trace(go.Scatter(x=x*100, y=stats.beta.pdf(x, 1 + variant_conv, 1 + variant_users - variant_conv),
                             name="B", fill="tozeroy", line=dict(color="#2ca02c"), opacity=0.7))
    fig.update_layout(height=320, xaxis_title="True click rate (%)", yaxis_title="Density",
                      margin=dict(l=10, r=10, t=10, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Each curve shows the plausible true click rate for that link. The more they overlap, the less certain we are.")

with tab3:
    a, b = st.columns(2)
    a.metric("Test power", f"{power*100:.1f}%")
    if power < 0.80:
        b.warning("⚠️ Not much data. Be cautious about the result.")
    else:
        b.success("✅ Enough data to trust the result.")
    st.caption("Power is the chance the test catches a real difference if one exists. 80% or more is the usual standard.")
