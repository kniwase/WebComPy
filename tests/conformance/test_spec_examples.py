from __future__ import annotations

import json
from pathlib import Path

import pytest

from ._spec_examples import (
    SPEC_EXAMPLE_COUNT,
    SPEC_REVISION,
    SPEC_SHA256,
    SpecExample,
    extract_examples,
    load_xfail_data,
    load_xfail_numbers,
    slugify,
)


@pytest.fixture(scope="module")
def examples() -> list[SpecExample]:
    return extract_examples()


class TestExtraction:
    def test_total_count_pinned(self, examples: list[SpecExample]) -> None:
        assert len(examples) == SPEC_EXAMPLE_COUNT

    def test_numbers_are_sequential_from_one(self, examples: list[SpecExample]) -> None:
        assert [ex.number for ex in examples] == list(range(1, len(examples) + 1))

    def test_every_example_has_section(self, examples: list[SpecExample]) -> None:
        assert all(ex.section.strip() for ex in examples)

    def test_first_example_is_tab_code_block(self, examples: list[SpecExample]) -> None:
        first = examples[0]
        assert first.number == 1
        assert first.section == "Tabs"
        assert "\t" in first.markdown

    def test_known_atx_heading_example(self, examples: list[SpecExample]) -> None:
        atx_examples = [ex for ex in examples if ex.section == "ATX headings"]
        assert atx_examples
        sample = next(ex for ex in atx_examples if ex.markdown == "# foo *bar* \\*baz\\*")
        assert sample.expected_html == "<h1>foo <em>bar</em> *baz*</h1>"

    def test_closing_fence_clears_state(self, examples: list[SpecExample]) -> None:
        assert examples[0].expected_html.startswith("<pre><code>")
        assert examples[0].expected_html.endswith("</code></pre>")

    def test_tab_marker_converted_in_markdown_and_html(self, examples: list[SpecExample]) -> None:
        examples_with_tabs = [ex for ex in examples if "\t" in ex.markdown]
        assert examples_with_tabs
        for ex in examples_with_tabs:
            assert "\u2192" not in ex.markdown
            assert "\u2192" not in ex.expected_html


class TestSlugify:
    @pytest.mark.parametrize(
        "section,expected",
        [
            ("ATX headings", "atx-headings"),
            ("Entity and numeric character references", "entity-and-numeric-character-references"),
            ("Tables (extension)", "tables-extension"),
            ("___", "general"),
        ],
    )
    def test_slugify(self, section: str, expected: str) -> None:
        assert slugify(section) == expected


class TestXfailLoader:
    def test_missing_file_returns_empty_set(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.json"
        assert load_xfail_numbers(path) == set()

    def test_missing_file_returns_empty_data(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.json"
        data = load_xfail_data(path)
        assert data.xfail_examples == set()
        assert data.baseline_passing == SPEC_EXAMPLE_COUNT
        assert data.baseline_xfailing == 0

    def test_parses_xfail_json_structure(self, tmp_path: Path) -> None:
        path = tmp_path / "xfail.json"
        path.write_text(
            json.dumps(
                {
                    "spec_revision": "abc",
                    "spec_sha256": "def",
                    "baseline": {"passing": 1, "xfailing": 2, "total": 3},
                    "generated_at": "2026-07-25",
                    "xfail_examples": [4, 5, 6],
                }
            ),
            encoding="utf-8",
        )
        data = load_xfail_data(path)
        assert data.spec_revision == "abc"
        assert data.spec_sha256 == "def"
        assert data.baseline_passing == 1
        assert data.baseline_xfailing == 2
        assert data.baseline_total == 3
        assert data.generated_at == "2026-07-25"
        assert data.xfail_examples == {4, 5, 6}
        assert load_xfail_numbers(path) == {4, 5, 6}


class TestXfailDataValidation:
    def test_xfail_examples_in_range(self) -> None:
        data = load_xfail_data()
        assert data.xfail_examples
        assert all(1 <= n <= SPEC_EXAMPLE_COUNT for n in data.xfail_examples)

    def test_xfail_spec_revision_matches_pin(self) -> None:
        data = load_xfail_data()
        assert data.spec_revision == SPEC_REVISION

    def test_xfail_spec_sha256_matches_pin(self) -> None:
        data = load_xfail_data()
        assert data.spec_sha256 == SPEC_SHA256

    def test_baseline_total_matches_example_count(self) -> None:
        data = load_xfail_data()
        assert data.baseline_total == SPEC_EXAMPLE_COUNT

    def test_baseline_passing_plus_xfailing_equals_total(self) -> None:
        data = load_xfail_data()
        assert data.baseline_passing + data.baseline_xfailing == data.baseline_total

    def test_baseline_xfailing_matches_examples_array_length(self) -> None:
        data = load_xfail_data()
        assert data.baseline_xfailing == len(data.xfail_examples)

    def test_xfail_examples_unique(self) -> None:
        raw = json.loads(Path(__file__).parent.joinpath("xfail.json").read_text(encoding="utf-8"))
        examples = raw["xfail_examples"]
        assert len(examples) == len(set(examples))
