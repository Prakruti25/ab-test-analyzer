"""
Story Checker: compare two versions of the same story.

Paste two links (or the text itself). The app shows where the sources agree,
where they conflict, and which differences are tiny rounding gaps. It does
not decide which source is true; it shows what needs to be verified.
"""

import sys
from pathlib import Path

# Make `src/` importable when streamlit runs this from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.source_compare import (
    compare_sources, fetch_article_text, score_against_reference,
)

st.set_page_config(page_title="Story Checker", page_icon="🔗", layout="wide")

for key in ("url_a", "url_b", "txt_a", "txt_b", "ref"):
    st.session_state.setdefault(key, "")


@st.cache_data(ttl=600, show_spinner=False)
def cached_fetch(url: str) -> str:
    return fetch_article_text(url)


def resolve_text(label: str, url: str, pasted: str) -> str:
    """Use the link if given; otherwise (or if it fails) use the pasted text."""
    url, pasted = url.strip(), pasted.strip()
    if url:
        try:
            return cached_fetch(url)
        except Exception:
            if pasted:
                st.info(f"Couldn't read {label} from its link, so I used the text you pasted.")
            else:
                st.warning(
                    f"Couldn't read **{label}** from that link (some sites block automated "
                    f"readers). Open “Link not working?” under it and paste the text instead."
                )
    return pasted


def pct(x: float) -> str:
    return f"{x*100:.2f}%" if x < 0.01 else f"{x*100:.1f}%"


# === HEADER ===
st.title("🔗 Story Checker")
st.markdown(
    "Two websites report the **same story**. Paste both links and this tool shows "
    "**what they agree on and where they differ**, such as different numbers or figures, "
    "so you know exactly what to verify."
)
st.caption(
    "It doesn't decide which source is true. It finds the disagreements, "
    "and tells you whether each one is big or just rounding."
)

# === INPUT (a form, so nothing runs until you press Compare) ===
with st.form("compare_form"):
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("🔗 Link to Source A", key="url_a", placeholder="https://…")
        with st.expander("Link not working? Paste the text instead"):
            st.text_area("Source A text", key="txt_a", height=140)
    with col2:
        st.text_input("🔗 Link to Source B", key="url_b", placeholder="https://…")
        with st.expander("Link not working? Paste the text instead"):
            st.text_area("Source B text", key="txt_b", height=140)

    with st.expander("➕ Optional: add an official reference (press release, court order, etc.)"):
        st.text_area("Reference text", key="ref", height=110)

    submitted = st.form_submit_button("Compare", type="primary")

if submitted:
    text_a = resolve_text("Source A", st.session_state["url_a"], st.session_state["txt_a"])
    text_b = resolve_text("Source B", st.session_state["url_b"], st.session_state["txt_b"])
    st.session_state["result"] = (
        {"a": text_a, "b": text_b, "ref": st.session_state["ref"].strip()}
        if text_a and text_b else None
    )
    if not (text_a and text_b):
        st.session_state["result"] = None

data = st.session_state.get("result")

# === RESULTS ===
if data:
    result = compare_sources(data["a"], data["b"])
    major, minor = result.major_conflicts, result.minor_conflicts
    figures = len(result.shared_numbers)

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Figures both sources agree on", figures)
    m2.metric("Real conflicts", len(major))
    m3.metric("Minor rounding differences", len(minor))

    if major:
        st.warning(
            f"⚠️ **{len(major)} real conflict(s) found.** "
            f"Verify these against a primary source before relying on either version."
        )
    elif minor:
        st.success(
            f"✅ **All main figures match.** Only {len(minor)} tiny difference(s), "
            f"most likely rounding or the sites updating at different times."
        )
    elif figures:
        st.success("✅ **No conflicts found.** Both sources give the same figures.")
    else:
        st.info(
            "No shared figures were found to compare. These pages may not report "
            "the same facts, or the text couldn't be read properly."
        )

    for i, c in enumerate(major, 1):
        with st.container(border=True):
            st.markdown(f"**🔴 Conflict {i}**")
            x, y = st.columns(2)
            x.markdown(f"**Source A says**\n\n> {c.sentence_a}")
            y.markdown(f"**Source B says**\n\n> {c.sentence_b}")
            x.caption("Differing figures: " + ", ".join(sorted(c.numbers_a - c.numbers_b)))
            y.caption("Differing figures: " + ", ".join(sorted(c.numbers_b - c.numbers_a)))

    for i, c in enumerate(minor, 1):
        with st.container(border=True):
            st.markdown(f"**🟡 Minor difference {i}**  ·  gap of about {pct(c.max_rel_diff)}")
            x, y = st.columns(2)
            x.markdown(f"**Source A says**\n\n> {c.sentence_a}")
            y.markdown(f"**Source B says**\n\n> {c.sentence_b}")
            x.caption("Differing figures: " + ", ".join(sorted(c.numbers_a - c.numbers_b)))
            y.caption("Differing figures: " + ", ".join(sorted(c.numbers_b - c.numbers_a)))

    with st.expander("✅ Figures both sources agree on"):
        st.write(", ".join(sorted(result.shared_numbers)) or "—")

    with st.expander("📄 What the tool read from each page"):
        r1, r2 = st.columns(2)
        r1.caption(f"Source A ({len(data['a']):,} characters)")
        r1.text(data["a"][:1500] + ("…" if len(data["a"]) > 1500 else ""))
        r2.caption(f"Source B ({len(data['b']):,} characters)")
        r2.text(data["b"][:1500] + ("…" if len(data["b"]) > 1500 else ""))

    if data["ref"]:
        st.divider()
        st.subheader("📌 Closeness to the reference")
        sa = score_against_reference(data["ref"], data["a"])
        sb = score_against_reference(data["ref"], data["b"])
        q1, q2 = st.columns(2)
        q1.metric("Source A matches the reference on", f"{sa.coverage*100:.0f}% of its facts")
        q1.caption(f"{sa.conflicts} contradicting claim(s)")
        q2.metric("Source B matches the reference on", f"{sb.coverage*100:.0f}% of its facts")
        q2.caption(f"{sb.conflicts} contradicting claim(s)")

        if (sa.conflicts, -sa.coverage) < (sb.conflicts, -sb.coverage):
            st.success("**Source A is closer to the reference.**")
        elif (sb.conflicts, -sb.coverage) < (sa.conflicts, -sa.coverage):
            st.success("**Source B is closer to the reference.**")
        else:
            st.info("Both sources are equally close to the reference.")
        st.caption(
            "This is only as reliable as the reference you chose. It shows agreement "
            "with that text, not proof of truth."
        )
