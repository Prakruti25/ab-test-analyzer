"""
Compare two versions of the same story and surface where they agree and
where they conflict (numbers, names). It does NOT decide which is true: it
tells a reader or editor exactly which claims need to be verified.
"""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

# --- number extraction -------------------------------------------------------
_NUM_RE = re.compile(
    r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*"
    r"(%|per\s?cent|percent|crore|lakh|million|billion|trillion|thousand)?",
    re.IGNORECASE,
)
_UNIT_MAP = {"percent": "%", "per cent": "%", "percent ": "%"}

# --- name extraction ---------------------------------------------------------
_NAME_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")
_STOPWORDS = {
    "The", "A", "An", "In", "On", "At", "It", "He", "She", "They", "This", "That",
    "These", "Those", "But", "And", "Or", "As", "By", "For", "From", "With", "After",
    "Before", "However", "Also", "His", "Her", "Their", "We", "I", "If", "When",
    "While", "Of", "To", "Is", "Was", "Were", "Be", "Has", "Have", "Had",
}


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
        u = "%" if u in ("percent", "per cent", "per  cent", "percent", "per cent") or u.startswith("per") else u
        found.add(f"{v}{u}")
    return found


def extract_names(text: str) -> set[str]:
    """Capitalised word sequences (people, places, organisations)."""
    names = set()
    for sentence in split_sentences(text):
        for m in _NAME_RE.finditer(sentence):
            name = m.group(0)
            words = name.split()
            # drop a leading stopword, e.g. 'The City Council' -> 'City Council'
            while words and words[0] in _STOPWORDS:
                words = words[1:]
            if not words:
                continue
            # a single capitalised word at the start of a sentence is just grammar
            if m.start() == 0 and len(words) == 1:
                continue
            names.add(" ".join(words))
    return names


def _content_words(sentence: str) -> set[str]:
    words = re.findall(r"[a-zA-Z]+", sentence.lower())
    return {w for w in words if len(w) > 3}


def _similarity(s1: str, s2: str) -> float:
    a, b = _content_words(s1), _content_words(s2)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class Conflict:
    sentence_a: str
    sentence_b: str
    numbers_a: set
    numbers_b: set


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


def find_conflicts(text_a: str, text_b: str, min_similarity: float = 0.35) -> list[Conflict]:
    """
    Pair up sentences that talk about the same thing, then flag the pairs whose
    numbers disagree (both sentences have numbers, and neither set contains the other).
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
        if best is None or best_score < min_similarity:
            continue
        nums_b = extract_numbers(best)
        if nums_b and not (nums_a <= nums_b or nums_b <= nums_a):
            conflicts.append(Conflict(sa, best, nums_a, nums_b))
    return conflicts


def compare_sources(text_a: str, text_b: str) -> Comparison:
    if not text_a.strip() or not text_b.strip():
        raise ValueError("Both sources need some text.")
    na, nb = extract_numbers(text_a), extract_numbers(text_b)
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
    conflicts: int         # sentences where the source's numbers contradict the reference
    matched: set
    missing: set


def score_against_reference(reference: str, source: str) -> ReferenceScore:
    """How closely a source matches a trusted reference text (e.g. an official statement)."""
    ref_facts = extract_numbers(reference) | extract_names(reference)
    src_facts = extract_numbers(source) | extract_names(source)
    matched = ref_facts & src_facts
    coverage = len(matched) / len(ref_facts) if ref_facts else 0.0
    return ReferenceScore(
        coverage=coverage,
        conflicts=len(find_conflicts(source, reference)),
        matched=matched,
        missing=ref_facts - src_facts,
    )


# --- fetching an article from a link ----------------------------------------
class _ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip = 0
        self._in_p = 0
        self._buf: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        elif tag in ("p", "h1"):
            self._in_p += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
        elif tag in ("p", "h1") and self._in_p:
            self._in_p -= 1
            text = " ".join(self._buf).strip()
            self._buf = []
            if len(text) > 25:
                if not text.endswith((".", "!", "?", '"', "”")):
                    text += "."
                self.paragraphs.append(text)

    def handle_data(self, data):
        if self._in_p and not self._skip and data.strip():
            self._buf.append(data.strip())


def html_to_text(html: str) -> str:
    parser = _ArticleParser()
    parser.feed(html)
    return "\n".join(parser.paragraphs)


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
