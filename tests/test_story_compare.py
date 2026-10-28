import pytest

from src.story_compare import (
    compare_sources, extract_names, extract_numbers, find_conflicts,
    html_to_text, score_against_reference,
)

A = ("The City Council approved a budget of 4.5 billion rupees on Tuesday. "
     "The budget raises property tax by 12 percent. "
     "Mayor Rajesh Mehta said road repairs will receive 300 crore.")
B = ("The City Council passed a budget of 4.8 billion rupees on Tuesday. "
     "The budget raises property tax by 12 percent. "
     "Mayor Rajesh Mehta said road repairs will receive 350 crore.")


def test_extract_numbers_normalises_units():
    assert extract_numbers("up 12 percent and 12% too") == {"12%"}
    assert "4.5billion" in extract_numbers("a budget of 4.5 billion")
    assert "1500" in extract_numbers("about 1,500 people")


def test_extract_names_ignores_sentence_start():
    names = extract_names("Yesterday it rained. Mayor Rajesh Mehta spoke in Ahmedabad.")
    assert "Mayor Rajesh Mehta" in names
    assert "Ahmedabad" in names
    assert "Yesterday" not in names


def test_conflicts_found_where_numbers_differ():
    conflicts = find_conflicts(A, B)
    assert len(conflicts) == 2  # budget size and road repairs
    assert all("12" not in c.sentence_a for c in conflicts)


def test_identical_sources_have_no_conflicts():
    result = compare_sources(A, A)
    assert result.conflicts == []
    assert result.similarity == pytest.approx(1.0)
    assert not result.only_a_numbers and not result.only_b_numbers


def test_shared_and_unique_numbers():
    result = compare_sources(A, B)
    assert "12%" in result.shared_numbers
    assert "4.5billion" in result.only_a_numbers
    assert "4.8billion" in result.only_b_numbers


def test_different_names_detected():
    r = compare_sources("Mayor Rajesh Mehta spoke.", "Mayor Rakesh Mehta spoke.")
    assert "Mayor Rajesh Mehta" in r.only_a_names
    assert "Mayor Rakesh Mehta" in r.only_b_names


def test_reference_scoring_prefers_matching_source():
    ref = B  # pretend B is the official statement
    score_a = score_against_reference(ref, A)
    score_b = score_against_reference(ref, B)
    assert score_b.conflicts == 0 and score_b.coverage == pytest.approx(1.0)
    assert score_a.conflicts == 2 and score_a.coverage < score_b.coverage


def test_empty_text_rejected():
    with pytest.raises(ValueError):
        compare_sources("", "something")


def test_html_to_text_extracts_paragraphs_only():
    html = ("<html><script>var x=1;</script><h1>Budget approved by council today</h1>"
            "<p>The council voted 28 to 12 on Tuesday evening</p><p>ok</p></html>")
    text = html_to_text(html)
    assert "28 to 12" in text and "var x" not in text


# --- clearer results for real pages -----------------------------------------
GOLD_A = ("Today's gold price in Ahmedabad stands at ₹14,400.00 per gram for 24 karat gold, "
          "₹13,200.00 per gram for 22 karat gold, and ₹10,800.00 per gram for 18 karat gold.")
GOLD_B = ("Today's gold price in Ahmedabad stands at ₹14,400 per gram for 24 karat gold, "
          "₹13,200 per gram for 22 karat gold, and ₹10,801 per gram for 18 karat gold.")


def test_tiny_difference_is_minor():
    result = compare_sources(GOLD_A, GOLD_B)
    assert len(result.conflicts) == 1
    assert result.conflicts[0].minor
    assert result.major_conflicts == [] and len(result.minor_conflicts) == 1


def test_big_difference_is_major():
    result = compare_sources(A, B)
    assert len(result.major_conflicts) == 2
    assert result.minor_conflicts == []


def test_years_not_counted_as_figures():
    result = compare_sources("Report from 2026 shows 5 people", "Report from 2026 shows 5 people")
    assert "2026" not in result.shared_numbers
    assert "5" in result.shared_numbers


def test_boilerplate_paragraphs_removed():
    html = ("<p>The council voted 28 to 12 on Tuesday evening</p>"
            "<p>Copyright 2026 Some Company Pvt Ltd. All Rights Reserved.</p>"
            "<footer><p>Footer text that is long enough to be kept otherwise</p></footer>")
    text = html_to_text(html)
    assert "28 to 12" in text
    assert "Rights Reserved" not in text and "Footer text" not in text


def test_repeated_paragraphs_deduplicated():
    html = "<p>The council voted 28 to 12 on Tuesday evening</p>" * 3
    assert html_to_text(html).count("28 to 12") == 1
