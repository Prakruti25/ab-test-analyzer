"""
Compare two versions of the same story and surface where they agree and
where they conflict (numbers, names). It does NOT decide which is true: it
tells a reader or editor exactly which claims need to be verified.
"""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Optional

# --- number extraction -------------------------------------------------------
_NUM_RE = re.compile(
    r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*"
    r"(%|per\s?cent|percent|crore|lakh|million|billion|trillion|thousand)?",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"^(19|20)\d{2}$")

# A difference smaller than this (relative) is treated as rounding / timing.
MINOR_DIFF_THRESHOLD = 0.001  # 0.1%

# --- name extraction ---------------------------------------------------------
_NAME_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")
_STOPWORDS = {
    "The", "A", "An", "In", "On", "At", "It", "He", "She", "They", "This", "That",
    "These", "Those", "But", "And", "Or", "As", "By", "For", "From", "With", "After",
    "Before", "However", "Also", "His", "Her", "Their", "We", "I", "If", "When",
    "While", "Of", "To", "Is", "Was", "Were", "Be", "Has", "Have", "Had",
}

# Paragraphs containing these are page furniture, not story content.
_BOILERPLATE = (
    "all rights reserved", "privacy policy", "terms of use", "terms & conditions",
    "terms and conditions", "cookie", "subscribe", "follow us", "download the app",
    "copyright", "©", "disclaimer", "advertisement", "sign up", "newsletter",
)


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def extract_numbers(text: str) -> set[str]:
    """Numbers normalised to strings like '12%', '4.5billion', '300crore', '28'."""
    found = set()
    for value, unit in _NUM_RE.findall(text):
        v = value.replace(",", "")
        try:
            v = f"{float(v):g}"
        except ValueError:
            continue
        u = (unit or "").lower().strip()
        if u.startswith("per"):
            u = "%"
        found.add(f"{v}{u}")
    return found


def extract_names(text: str) -> set[str]:
    """Capitalised word sequences (people, places, organisations)."""
    names = set()
    for sentence in split_sentences(text):
        for m in _NAME_RE.finditer(sentence):
            words = m.group(0).split()
            while words and words[0] in _STOPWORDS:
                words = words[1:]
            if not words:
                continue
            if m.start() == 0 and len(words) == 1:
                continue
            names.add(" ".join(words))
    return names


def _content_words(sentence: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z]+", sentence.lower()) if len(w) > 3}


def _similarity(s1: str, s2: str) -> float:
    a, b = _content_words(s1), _content_words(s2)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _parse(token: str) -> tuple[float, str]:
    m = re.match(r"^([\d.]+)(.*)$", token)
    return float(m.group(1)), m.group(2)


def _max_relative_difference(only_a: set[str], only_b: set[str]) -> Optional[float]:
    """
    Pair up the numbers that differ and return the largest relative gap.
    Returns None when they can't be paired cleanly (treated as a real conflict).
    """
    if not only_a or len(only_a) != len(only_b):
        return None
    pa = sorted(_parse(t) for t in only_a)
    pb = sorted(_parse(t) for t in only_b)
    worst = 0.0
    for (va, ua), (vb, ub) in zip(pa, pb):
        if ua != ub:
            return None
        top = max(abs(va), abs(vb))
        if top == 0:
            continue
        worst = max(worst, abs(va - vb) / top)
    return worst


@dataclass
class Conflict:
    sentence_a: str
    sentence_b: str
    numbers_a: set
    numbers_b: set
    max_rel_diff: Optional[float] = None

    @property
    def minor(self) -> bool:
        """True when the numbers differ only by a tiny amount (rounding / update timing)."""
        return self.max_rel_diff is not None and self.max_rel_diff <= MINOR_DIFF_THRESHOLD


@dataclass
class Comparison:
    similarity: float
    shared_numbers: set
    only_a_numbers: set
    only_b_numbers: set
    shared_names: set
    only_a_names: set
    only_b_names: set
    conflicts: list = field(default_factory=list)

    @property
    def major_conflicts(self) -> list:
        return [c for c in self.conflicts if not c.minor]

    @property
    def minor_conflicts(self) -> list:
        return [c for c in self.conflicts if c.minor]


def find_conflicts(text_a: str, text_b: str) -> list[Conflict]:
    """
    Pair up sentences that talk about the same thing, then flag the pairs whose
    numbers disagree (both have numbers, and neither set contains the other).
    """
    conflicts = []
    sentences_b = split_sentences(text_b)
    for sa in split_sentences(text_a):
        nums_a = extract_numbers(sa)
        if not nums_a:
            continue
        best, best_score = None, 0.0
        for sb in sentences_b:
            score = _similarity(sa, sb)
            if score > best_score:
                best, best_score = sb, score
        if best is None:
            continue
        nums_b = extract_numbers(best)
        # Sentences with no figure in common need to be very similar to count as "the same claim".
        required = 0.35 if (nums_a & nums_b) else 0.5
        if best_score < required:
            continue
        if nums_b and not (nums_a <= nums_b or nums_b <= nums_a):
            rel = _max_relative_difference(nums_a - nums_b, nums_b - nums_a)
            conflicts.append(Conflict(sa, best, nums_a, nums_b, rel))
    return conflicts


def _drop_years(numbers: set[str]) -> set[str]:
    return {n for n in numbers if not _YEAR_RE.match(n)}


def compare_sources(text_a: str, text_b: str) -> Comparison:
    if not text_a.strip() or not text_b.strip():
        raise ValueError("Both sources need some text.")
    na, nb = _drop_years(extract_numbers(text_a)), _drop_years(extract_numbers(text_b))
    ea, eb = extract_names(text_a), extract_names(text_b)
    wa, wb = _content_words(text_a), _content_words(text_b)
    similarity = len(wa & wb) / len(wa | wb) if (wa | wb) else 0.0
    return Comparison(
        similarity=similarity,
        shared_numbers=na & nb,
        only_a_numbers=na - nb,
        only_b_numbers=nb - na,
        shared_names=ea & eb,
        only_a_names=ea - eb,
        only_b_names=eb - ea,
        conflicts=find_conflicts(text_a, text_b),
    )


@dataclass
class ReferenceScore:
    coverage: float        # share of the reference's facts the source repeats
    conflicts: int         # real (non-minor) contradictions with the reference
    matched: set
    missing: set


def score_against_reference(reference: str, source: str) -> ReferenceScore:
    """How closely a source matches a trusted reference text (e.g. an official statement)."""
    ref_facts = extract_numbers(reference) | extract_names(reference)
    src_facts = extract_numbers(source) | extract_names(source)
    matched = ref_facts & src_facts
    coverage = len(matched) / len(ref_facts) if ref_facts else 0.0
    real = [c for c in find_conflicts(source, reference) if not c.minor]
    return ReferenceScore(coverage=coverage, conflicts=len(real),
                          matched=matched, missing=ref_facts - src_facts)


# --- fetching an article from a link ----------------------------------------
class _ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip = 0
        self._in_p = 0
        self._buf: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "footer", "nav"):
            self._skip += 1
        elif tag in ("p", "h1"):
            self._in_p += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "footer", "nav") and self._skip:
            self._skip -= 1
        elif tag in ("p", "h1") and self._in_p:
            self._in_p -= 1
            text = " ".join(self._buf).strip()
            self._buf = []
            if len(text) > 25 and not any(b in text.lower() for b in _BOILERPLATE):
                if not text.endswith((".", "!", "?", '"', "”")):
                    text += "."
                self.paragraphs.append(text)

    def handle_data(self, data):
        if self._in_p and not self._skip and data.strip():
            self._buf.append(data.strip())


def html_to_text(html: str) -> str:
    parser = _ArticleParser()
    parser.feed(html)
    seen, unique = set(), []
    for p in parser.paragraphs:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return "\n".join(unique)


def fetch_article_text(url: str, timeout: int = 10) -> str:
    """Download a page and return its paragraph text. Raises on failure."""
    import requests

    resp = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0 (compatible; SourceCompare/1.0)"},
    )
    resp.raise_for_status()
    text = html_to_text(resp.text)
    if not text:
        raise ValueError("Couldn't find article text on that page.")
    return text
