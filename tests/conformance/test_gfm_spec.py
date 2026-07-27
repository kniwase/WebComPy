from __future__ import annotations

import json
from pathlib import Path

import pytest

from webcompy.template._markdown_default import DefaultMarkdownParser

from ._spec_examples import (
    XFAIL_JSON_PATH,
    SpecExample,
    extract_examples,
    load_xfail_numbers,
    slugify,
)

EXAMPLES: list[SpecExample] = extract_examples()
XFAIL_NUMBERS: set[int] = load_xfail_numbers()

BLOCK_SECTIONS: frozenset[str] = frozenset(
    {
        "Tabs",
        "Thematic breaks",
        "ATX headings",
        "Setext headings",
        "Indented code blocks",
        "Fenced code blocks",
        "HTML blocks",
        "Block quotes",
        "List items",
        "Lists",
        "Precedence",
        "Link reference definitions",
        "Paragraphs",
        "Blank lines",
        "Tables (extension)",
        "Task list items (extension)",
    }
)


def _matches(parser: DefaultMarkdownParser, example: SpecExample) -> bool:
    return parser.render(example.markdown).rstrip() == example.expected_html.rstrip()


@pytest.mark.parametrize(
    "example",
    [
        pytest.param(
            ex,
            marks=pytest.mark.xfail(reason="GFM deviation", strict=True) if ex.number in XFAIL_NUMBERS else (),
            id=f"{ex.number:04d}-{slugify(ex.section)}",
        )
        for ex in EXAMPLES
    ],
)
def test_gfm_spec(example: SpecExample) -> None:
    assert _matches(DefaultMarkdownParser(), example)


def test_gfm_conformance_rate() -> None:
    parser = DefaultMarkdownParser()
    passed = sum(1 for ex in EXAMPLES if _matches(parser, ex))
    total = len(EXAMPLES)
    print(f"\nGFM conformance: {passed}/{total} ({passed / total:.1%})")


def test_block_section_xfails_have_notes() -> None:
    raw = json.loads(Path(XFAIL_JSON_PATH).read_text(encoding="utf-8"))
    notes: dict[str, str] = raw.get("notes", {})
    xfail_examples: list[int] = raw.get("xfail_examples", [])
    examples_by_number = {ex.number: ex for ex in EXAMPLES}
    missing: list[tuple[int, str]] = []
    for n in xfail_examples:
        ex = examples_by_number.get(n)
        if ex is None:
            continue
        if ex.section in BLOCK_SECTIONS and str(n) not in notes:
            missing.append((n, ex.section))
    assert not missing, "Block-section xfail examples without notes in xfail.json: " + ", ".join(
        f"Ex {n} [{sec}]" for n, sec in missing
    )
