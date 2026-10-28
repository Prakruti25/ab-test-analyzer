"""
A/B Test Analyzer + Source Comparison.

Tab 1: Compare two versions of the same story (pasted text or links) and see
       exactly where they agree and where they conflict.
Tab 2: Headline A/B test: which of two headlines do readers prefer, and is
       the difference real or just luck?
"""

import sys
from pathlib import Path

# Make `src/` importable when streamlit runs this from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.bayesian import bayesian_conversion_test
from src.frequentist import two_proportion_z_test
from src.source_compare import (
    compare_sources, fetch_article_text, score_against_reference,
)

ALPHA = 0.05
MEANINGFUL_LIFT = 0.01

st.set_page_config(page_title="Story Checker & A/B Analyzer", page_icon="🔗", layout="wide")

# === EXAMPLE DATA ===
EXAMPLE_A = (
    "The City Council approved a budget of 4.5 billion rupees on Tuesday. "
    "The budget raises property tax by 12 percent. "
    "Mayor Rajesh Mehta said road repairs will receive 300 crore. "
    "The vote was 28 to 12."
)
EXAMPLE_B = (
    "The City Council passed a budget of 4.8 billion rupees on Tuesday. "
    "The budget raises property tax by 12 percent. "
    "Mayor Rajesh Mehta said road repairs will receive 350 crore. "
    "The vote was 28 to 12."
)
EXAMPLE_REF = (
    "Official statement: The City Council approved a budget of 4.8 billion rupees. "
    "Property tax will rise by 12 percent. Mayor Rajesh Mehta confirmed 350 crore "
    "for road repairs. The vote was 28 to 12."
)

for key, val in {
    "src_a": "", "src_b": "", "ref": "", "url_a": "", "url_b": "",
    "name_a": "Headline A: 'City Council Approves New Budget'",
    "name_b": "Headline B: 'How the New Budget Will Affect You'",
    "cu": 4200, "cc": 310, "vu": 4150, "vc": 365,
}.items():
    st.session_state.setdefault(key, val)


def load_example():
    st.session_state["src_a"] = EXAMPLE_A
    st.session_state["src_b"] = EXAMPLE_B
    st.session_state["ref"] = EXAMPLE_REF
    st.session_state["url_a"] = ""
    st.session_state["url_b"] = ""


@st.cache_data(ttl=600, show_spinner=False)
def cached_fetch(url: str) -> str:
    return fetch_article_text(url)


def resolve_text(label: str, url: str, pasted: str) -> str:
    """Use pasted text if present; otherwise try to download the link."""
    if pasted.strip():
        return pasted
    if url.strip():
        try:
            return cached_fetch(url.strip())
        except Exception:
            st.warning(
                f"Couldn't read {label} from that link (some sites block automated "
                f"readers). Please paste the article text instead."
            )
    return ""


st.title("🔗 Story Checker & A/B Analyzer")
tab_compare, tab_ab = st.tabs(["📰 Compare two sources", "📊 Headline A/B test"])

# =============================================================================
# TAB 1: SOURCE COMPARISON
# =============================================================================
with tab_compare:
    st.markdown(
        "Two outlets report the **same story**. Paste both versions (or give links) and "
        "this tool shows **where they agree and where they conflict**, such as different "
        "numbers, names, or figures, so you know exactly what to verify."
    )
    st.info(
        "ℹ️ It doesn't decide which source is *true*. It finds the disagreements. "
        "Add an official reference below to see which source is closer to it."
    )
    st.button("📰 Load example", on_click=load_example)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Source A**")
        st.text_input("Link (optional)", key="url_a", placeholder="https://…")
        st.text_area("Or paste the text", key="src_a", height=180)
    with col2:
        st.markdown("**Source B**")
        st.text_input("Link (optional)", key="url_b", placeholder="https://…")
        st.text_area("Or paste the text", key="src_b", height=180)

    with st.expander("➕ Add an official reference (press release, court order, etc.)"):
        st.text_area("Reference text", key="ref", height=120)

    text_a = resolve_text("Source A", st.session_state["url_a"], st.session_state["src_a"])
    text_b = resolve_text("Source B", st.session_state["url_b"], st.session_state["src_b"])

    if not text_a or not text_b:
        st.caption("Add text or a link for both sources, or click **Load example**.")
    else:
        result = compare_sources(text_a, text_b)
        st.divider()

        m1, m2, m3 = st.columns(3)
        m1.metric("Facts both sources agree on", len(result.shared_numbers) + len(result.shared_names))
        m2.metric("Conflicting claims", len(result.conflicts))
        m3.metric("Wording overlap", f"{result.similarity*100:.0f}%")

        if result.conflicts:
            st.warning(
                f"⚠️ **{len(result.conflicts)} conflicting claim(s) found.** "
                f"These need to be verified against a primary source before publishing."
            )
        else:
            st.success("✅ **No conflicting numbers found.** The sources agree on the figures they share.")

        for i, c in enumerate(result.conflicts, 1):
            with st.container(border=True):
                st.markdown(f"**Conflict {i}**")
                x, y = st.columns(2)
                x.markdown(f"**Source A says**\n\n> {c.sentence_a}")
                x.caption("Numbers: " + ", ".join(sorted(c.numbers_a)))
                y.markdown(f"**Source B says**\n\n> {c.sentence_b}")
                y.caption("Numbers: " + ", ".join(sorted(c.numbers_b)))

        with st.expander("🔍 Names and numbers only one source mentions"):
            d1, d2 = st.columns(2)
            d1.markdown("**Only in A**")
            d1.write(", ".join(sorted(result.only_a_names | result.only_a_numbers)) or "—")
            d2.markdown("**Only in B**")
            d2.write(", ".join(sorted(result.only_b_names | result.only_b_numbers)) or "—")

        reference = st.session_state["ref"].strip()
        if reference:
            st.divider()
            st.subheader("📌 Closeness to the reference")
            sa = score_against_reference(reference, text_a)
            sb = score_against_reference(reference, text_b)
            r1, r2 = st.columns(2)
            r1.metric("Source A matches the reference on", f"{sa.coverage*100:.0f}% of its facts")
            r1.caption(f"{sa.conflicts} contradicting claim(s)")
            r2.metric("Source B matches the reference on", f"{sb.coverage*100:.0f}% of its facts")
            r2.caption(f"{sb.conflicts} contradicting claim(s)")

            if (sa.conflicts, -sa.coverage) < (sb.conflicts, -sb.coverage):
                st.success("**Source A is closer to the reference.**")
            elif (sb.conflicts, -sb.coverage) < (sa.conflicts, -sa.coverage):
                st.success("**Source B is closer to the reference.**")
            else:
                st.info("Both sources are equally close to the reference.")
            st.caption(
                "'Closer to the reference' is only as reliable as the reference you chose. "
                "It shows agreement with that text, not proof of truth."
            )

# =============================================================================
# TAB 2: HEADLINE A/B TEST
# =============================================================================
with tab_ab:
    st.markdown(
        "The same story has **two headlines**. Which one do readers prefer, and is the "
        "difference real or just luck?"
    )
    st.caption(
        "Showing sample data; in real use the numbers would come from a site's analytics."
    )

    with st.expander("✏️ Use your own numbers"):
        c1, c2 = st.columns(2)
        with c1:
            name_a = st.text_input("Name of first headline", key="name_a")
            control_users = st.number_input("Views (A)", 1, 10_000_000, key="cu")
            control_conv = st.number_input("Clicks (A)", 0, 10_000_000, key="cc")
        with c2:
            name_b = st.text_input("Name of second headline", key="name_b")
            variant_users = st.number_input("Views (B)", 1, 10_000_000, key="vu")
            variant_conv = st.number_input("Clicks (B)", 0, 10_000_000, key="vc")

    if control_conv > control_users or variant_conv > variant_users:
        st.error("Clicks can't be higher than views.")
    else:
        freq = two_proportion_z_test(control_conv, control_users, variant_conv, variant_users, alpha=ALPHA)
        bayes = bayesian_conversion_test(
            control_conv, control_users, variant_conv, variant_users,
            meaningful_lift_threshold=MEANINGFUL_LIFT,
        )

        st.divider()
        k1, k2, k3 = st.columns(3)
        k1.metric("A click rate", f"{freq.control_rate*100:.2f}%")
        k2.metric("B click rate", f"{freq.variant_rate*100:.2f}%", delta=f"{freq.absolute_lift*100:+.2f} pp")
        k3.metric("Chance B beats A", f"{bayes.prob_variant_better*100:.1f}%")

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
                f"⚖️ **No clear winner yet.** {leader} is ahead ({chance*100:.1f}% chance of being "
                f"better), but the gap is small enough that it could be luck. "
                f"**Recommendation: collect more data before deciding.**"
            )
