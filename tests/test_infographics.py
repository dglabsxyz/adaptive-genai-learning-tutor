"""Infographic generation must produce a valid, legible, source-backed SVG offline."""

from backend.infographics import generate_infographic, structural_check, _template_svg, intended_strings


def test_offline_infographic_is_template_and_structurally_sound():
    # No QWEN_API_KEY under pytest -> deterministic template, VL verification skipped.
    result = generate_infographic("Retrieval Augmented Generation", save=False)

    assert result["generator"].startswith("deterministic_template")
    sc = result["structural_check"]
    assert sc["ok"] is True
    assert sc["all_intended_present"] is True
    assert sc["min_font_size"] >= 16
    assert sc["text_element_count"] > 0
    assert result["legible_and_correct"] is True
    assert result["svg"].lstrip().startswith("<svg")
    assert result["svg"].rstrip().endswith("</svg>")
    # grounded in the corpus
    assert result["sources"]


def test_structural_check_detects_missing_text():
    content = {
        "title": "My Title",
        "subtitle": "Sub",
        "cards": [{"heading": "Card A", "record_type": "topic", "lines": ["line one"]}],
        "sources": [],
    }
    svg = _template_svg(content)
    intended = intended_strings(content)
    assert structural_check(svg, intended)["all_intended_present"] is True
    # A string that is not on the canvas should be reported missing.
    assert structural_check(svg, ["Totally Absent Heading"])["all_intended_present"] is False
