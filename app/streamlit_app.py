"""
Two Links, One Story — a simple A/B test analyzer.

Enter views and clicks for two links to the same story. The app tells you
which link readers prefer and whether the difference is real or just luck.
"""

import sys
from pathlib import Path

# Make `src/` importable when streamlit runs this from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.bayesian import bayesian_conversion_test
from src.frequentist import two_proportion_z_test

# Fixed, standard settings
ALPHA = 0.05
MEANINGFUL_LIFT = 0.01

st.set_page_config(page_title="Two Links, One Story", page_icon="🔗", layout="wide")

# === DEFAULTS: start on the sample example ===
st.session_state.setdefault("name_a", "Headline A: 'City Council Approves New Budget'")
st.session_state.setdefault("name_b", "Headline B: 'How the New Budget Will Affect You'")
st.session_state.setdefault("cu", 4200)
st.session_state.setdefault("cc", 310)
st.session_state.setdefault("vu", 4150)
st.session_state.setdefault("vc", 365)


# === HEADER ===
st.title("🔗 Two Links, One Story")
st.markdown(
    "A newspaper publishes the **same story under two links or headlines**. "
    "Enter how many readers saw each and how many clicked. "
    "This tells you **which one readers prefer — and whether the difference is real or just luck.**"
)
st.caption(
    "Measures reader engagement, not factual accuracy. "
    "Showing sample data; in real use the numbers would come from a site's analytics."
)

with st.expander("✏️ Use your own numbers"):
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

# === RESULT ===
st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("A click rate", f"{freq.control_rate*100:.2f}%")
c2.metric("B click rate", f"{freq.variant_rate*100:.2f}%", delta=f"{freq.absolute_lift*100:+.2f} pp")
c3.metric("Chance B beats A", f"{bayes.prob_variant_better*100:.1f}%")

p_b = bayes.prob_variant_better
if freq.significant and freq.absolute_lift > 0:
    st.success(
        f"🏆 **Winner: {name_b}.** Readers click it more, and the difference is real, "
        f"not luck. There is a {p_b*100:.1f}% chance it truly performs better. "
        f"**Recommendation: promote this link.**"
    )
elif freq.significant and freq.absolute_lift < 0:
    st.success(
        f"🏆 **Winner: {name_a}.** Readers click it more, and the difference is real, "
        f"not luck. There is a {(1-p_b)*100:.1f}% chance it truly performs better. "
        f"**Recommendation: promote this link.**"
    )
else:
    leader = name_b if freq.absolute_lift > 0 else name_a
    chance = p_b if freq.absolute_lift > 0 else 1 - p_b
    st.warning(
        f"⚖️ **No clear winner yet.** {leader} is ahead ({chance*100:.1f}% chance of being better), "
        f"but the gap is small enough that it could be luck. "
        f"**Recommendation: collect more data before deciding.**"
    )
