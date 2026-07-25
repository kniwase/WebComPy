from __future__ import annotations

import pytest

from webcompy.template._markdown_default import DefaultMarkdownParser

from ._spec_examples import (
    SpecExample,
    extract_examples,
    load_xfail_numbers,
    slugify,
)

EXAMPLES: list[SpecExample] = extract_examples()
XFAIL_NUMBERS: set[int] = load_xfail_numbers()


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
