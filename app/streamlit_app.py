"""
Two Headlines, One Story — a live A/B test.

Every visitor is randomly shown Headline A or Headline B. The app counts how
many people saw each headline and how many clicked, then tells you which
headline readers prefer and whether the difference is real or just luck.
"""

import random
import sys
import threading
from pathlib import Path

# Make `src/` importable when streamlit runs this from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import streamlit as st

from src.bayesian import bayesian_conversion_test
from src.frequentist import two_proportion_z_test

HEADLINES = {
    "A": "City Council Approves New Budget",
    "B": "How the New Budget Will Affect You",
}
ALPHA = 0.05
MEANINGFUL_LIFT = 0.01

st.set_page_config(page_title="Two Headlines, One Story", page_icon="🔗", layout="wide")


# === SHARED COUNTERS (shared by every visitor while the app is running) ===
@st.cache_resource
def get_store():
    return {
        "lock": threading.Lock(),
        "views": {"A": 0, "B": 0},
        "clicks": {"A": 0, "B": 0},
    }


store = get_store()


def add(kind, arm, n=1):
    with store["lock"]:
        store[kind][arm] += n


def on_click():
    if not st.session_state.clicked:
        add("clicks", st.session_state.arm)
        st.session_state.clicked = True


def simulate_traffic():
    """Demo only: add 5,000 simulated visitors per headline (true rates 7% and 9%)."""
    rng = np.random.default_rng()
    for arm, true_rate in (("A", 0.07), ("B", 0.09)):
        add("views", arm, 5000)
        add("clicks", arm, int(rng.binomial(5000, true_rate)))


def reset():
    with store["lock"]:
        for kind in ("views", "clicks"):
            for arm in ("A", "B"):
                store[kind][arm] = 0


# === ASSIGN THIS VISITOR TO A HEADLINE (randomly, once per visit) ===
if "arm" not in st.session_state:
    st.session_state.arm = random.choice(["A", "B"])
    st.session_state.clicked = False
    add("views", st.session_state.arm)


# === HEADER ===
st.title("🔗 Two Headlines, One Story")
st.markdown(
    "A newspaper has **one story with two possible headlines**. Each visitor is "
    "randomly shown one of them, and the app **automatically counts** who saw it "
    "and who clicked. Then it tells you **which headline readers prefer, and "
    "whether the difference is real or just luck.**"
)
st.caption("Measures reader engagement, not factual accuracy.")

# === THE EXPERIMENT: what this visitor sees ===
st.subheader("📰 Your headline")
with st.container(border=True):
    st.markdown(f"### {HEADLINES[st.session_state.arm]}")
    if st.session_state.clicked:
        st.success("✅ Your click was counted. Thanks!")
    else:
        st.button("Read the story →", on_click=on_click)

# === RESULTS ===
st.divider()
st.subheader("📊 Results so far")

with store["lock"]:
    views = dict(store["views"])
    clicks = dict(store["clicks"])

if views["A"] < 1 or views["B"] < 1:
    st.info("Waiting for more visitors. Each headline needs at least one view.")
    st.button("🔄 Refresh results")
else:
    freq = two_proportion_z_test(clicks["A"], views["A"], clicks["B"], views["B"], alpha=ALPHA)
    bayes = bayesian_conversion_test(
        clicks["A"], views["A"], clicks["B"], views["B"],
        meaningful_lift_threshold=MEANINGFUL_LIFT,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Headline A click rate", f"{freq.control_rate*100:.2f}%")
    c1.caption(f"{clicks['A']} clicks out of {views['A']} views")
    c2.metric("Headline B click rate", f"{freq.variant_rate*100:.2f}%",
              delta=f"{freq.absolute_lift*100:+.2f} pp")
    c2.caption(f"{clicks['B']} clicks out of {views['B']} views")
    c3.metric("Chance B beats A", f"{bayes.prob_variant_better*100:.1f}%")

    p_b = bayes.prob_variant_better
    name_a, name_b = f"“{HEADLINES['A']}”", f"“{HEADLINES['B']}”"
    if freq.significant and freq.absolute_lift > 0:
        st.success(
            f"🏆 **Winner: {name_b}.** Readers click it more, and the difference is real, "
            f"not luck. There is a {p_b*100:.1f}% chance it truly performs better. "
            f"**Recommendation: use this headline.**"
        )
    elif freq.significant and freq.absolute_lift < 0:
        st.success(
            f"🏆 **Winner: {name_a}.** Readers click it more, and the difference is real, "
            f"not luck. There is a {(1-p_b)*100:.1f}% chance it truly performs better. "
            f"**Recommendation: use this headline.**"
        )
    else:
        leader = name_b if freq.absolute_lift > 0 else name_a
        chance = p_b if freq.absolute_lift > 0 else 1 - p_b
        st.warning(
            f"⚖️ **No clear winner yet.** {leader} is ahead ({chance*100:.1f}% chance of being "
            f"better), but the gap is small enough that it could be luck. "
            f"**Recommendation: collect more visitors before deciding.**"
        )
    st.button("🔄 Refresh results")

# === DEMO TOOLS ===
with st.expander("🛠️ Demo tools"):
    st.caption(
        "A live test needs many visitors. To preview a busy day, you can add "
        "**simulated** traffic (5,000 fake visitors per headline, randomly generated). "
        "Simulated data is for demonstration only."
    )
    d1, d2 = st.columns(2)
    d1.button("➕ Simulate 5,000 visitors per headline", on_click=simulate_traffic)
    d2.button("🗑️ Reset all counts", on_click=reset)
