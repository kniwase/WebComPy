from __future__ import annotations

from pathlib import Path

import pytest

from ._spec_examples import (
    SPEC_EXAMPLE_COUNT,
    SpecExample,
    extract_examples,
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
    def test_empty_file_returns_empty_set(self, tmp_path: Path) -> None:
        path = tmp_path / "xfail.txt"
        path.write_text("", encoding="utf-8")
        assert load_xfail_numbers(path) == set()

    def test_missing_file_returns_empty_set(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.txt"
        assert load_xfail_numbers(path) == set()

    def test_parses_numbers_and_skips_comments(self, tmp_path: Path) -> None:
        path = tmp_path / "xfail.txt"
        path.write_text(
            "# header comment\n\n1\n2\n# another comment\n3\n\n",
            encoding="utf-8",
        )
        assert load_xfail_numbers(path) == {1, 2, 3}
