from __future__ import annotations

import pytest

from webcompy.template._markdown_blocks import (
    _Parser,
    parse_blocks,
)


class TestFindNextNonspace:
    def _state(self, line: str) -> _Parser:
        p = _Parser()
        p.current_line = line
        p.find_next_nonspace()
        return p

    def test_no_indent(self) -> None:
        p = self._state("foo bar")
        assert p.blank is False
        assert p.indent == 0
        assert p.next_nonspace == 0
        assert p.next_nonspace_column == 0
        assert p.indented is False

    def test_blank_line(self) -> None:
        p = self._state("")
        assert p.blank is True
        assert p.next_nonspace == 0

    def test_spaces_only(self) -> None:
        p = self._state("   ")
        assert p.blank is True
        assert p.next_nonspace == 3
        assert p.next_nonspace_column == 3

    def test_tab_to_column_four(self) -> None:
        p = self._state("\tfoo")
        assert p.blank is False
        assert p.next_nonspace == 1
        assert p.next_nonspace_column == 4
        assert p.indent == 4
        assert p.indented is True

    def test_two_spaces_then_tab(self) -> None:
        p = self._state("  \tfoo")
        assert p.next_nonspace == 3
        assert p.next_nonspace_column == 4
        assert p.indent == 4
        assert p.indented is True

    def test_four_spaces_then_tab(self) -> None:
        p = self._state("    \tfoo")
        assert p.next_nonspace == 5
        assert p.next_nonspace_column == 8
        assert p.indent == 8

    def test_two_tabs(self) -> None:
        p = self._state("\t\tfoo")
        assert p.next_nonspace == 2
        assert p.next_nonspace_column == 8

    @pytest.mark.parametrize(
        "line,expected_indent,expected_nonspace_col",
        [
            ("foo", 0, 0),
            ("  foo", 2, 2),
            ("\tfoo", 4, 4),
            ("  \tfoo", 4, 4),
            ("\t\tfoo", 8, 8),
            ("    \tfoo", 8, 8),
            ("\t  foo", 6, 6),
            ("   ", 3, 3),
        ],
    )
    def test_spec_tabs_indent_calculations(self, line: str, expected_indent: int, expected_nonspace_col: int) -> None:
        p = self._state(line)
        assert p.indent == expected_indent
        assert p.next_nonspace_column == expected_nonspace_col


class TestAdvanceOffset:
    def _parser(self, line: str) -> _Parser:
        p = _Parser()
        p.current_line = line
        return p

    def test_advance_one_char_non_columns(self) -> None:
        p = self._parser("foo")
        p.advance_offset(1, False)
        assert p.offset == 1

    def test_advance_columns_past_spaces(self) -> None:
        p = self._parser("   foo")
        p.advance_offset(3, True)
        assert p.offset == 3
        assert p.column == 3

    def test_advance_columns_through_full_tab(self) -> None:
        p = self._parser("\tfoo")
        p.advance_offset(4, True)
        assert p.offset == 1
        assert p.column == 4
        assert p.partially_consumed_tab is False

    def test_partial_tab_marks_state(self) -> None:
        p = self._parser("\tfoo")
        p.advance_offset(2, True)
        assert p.offset == 0
        assert p.column == 2
        assert p.partially_consumed_tab is True

    def test_tab_non_columns_advances_full_tab(self) -> None:
        p = self._parser("\tfoo")
        p.advance_offset(1, False)
        assert p.offset == 1
        assert p.column == 4
        assert p.partially_consumed_tab is False


class TestParseBlocksParagraph:
    def test_single_paragraph(self) -> None:
        r = parse_blocks("Hello world", lambda x: x)
        assert r.html == "<p>Hello world</p>"

    def test_paragraph_lines_joined_with_newline(self) -> None:
        r = parse_blocks("Hello\nworld", lambda x: x)
        assert r.html == "<p>Hello\nworld</p>"

    def test_paragraph_break_on_blank(self) -> None:
        r = parse_blocks("One\n\nTwo", lambda x: x)
        assert r.html == "<p>One</p>\n<p>Two</p>"

    def test_leading_blank_lines_ignored(self) -> None:
        r = parse_blocks("\n\n\nfoo", lambda x: x)
        assert r.html == "<p>foo</p>"

    def test_trailing_blank_lines_ignored(self) -> None:
        r = parse_blocks("foo\n\n\n", lambda x: x)
        assert r.html == "<p>foo</p>"

    def test_three_space_indent_still_paragraph(self) -> None:
        r = parse_blocks("   foo", lambda x: x)
        assert r.html == "<p>foo</p>"

    def test_nul_replaced(self) -> None:
        r = parse_blocks("a\x00b", lambda x: x)
        assert r.html == "<p>a\ufffdb</p>"


class TestInlineSeam:
    def test_inline_renders_paragraph_content(self) -> None:
        captured: list[str] = []

        def inline(text: str) -> str:
            captured.append(text)
            return f"<em>{text}</em>"

        parse_blocks("Hello world", inline)
        assert captured == ["Hello world"]

    def test_inline_receives_joined_lines(self) -> None:
        captured: list[str] = []

        def inline(text: str) -> str:
            captured.append(text)
            return text

        parse_blocks("Hello\nworld", inline)
        assert captured == ["Hello\nworld"]

    def test_multiple_paragraphs_each_inlined(self) -> None:
        captured: list[str] = []

        def inline(text: str) -> str:
            captured.append(text)
            return text

        parse_blocks("One\n\nTwo", inline)
        assert captured == ["One", "Two"]


class TestDedent:
    def test_multiline_source_is_dedented(self) -> None:
        source = "    foo\n    bar"
        r = parse_blocks(source, lambda x: x)
        assert r.html == "<p>foo\nbar</p>"

    def test_single_line_source_not_dedented(self) -> None:
        r = parse_blocks("    foo", lambda x: x)
        assert r.html == "<p>foo</p>"


class TestBlockQuote:
    def test_single_line(self) -> None:
        r = parse_blocks("> foo", lambda x: x)
        assert r.html == "<blockquote>\n<p>foo</p>\n</blockquote>"

    def test_multi_line_with_markers(self) -> None:
        r = parse_blocks("> foo\n> bar", lambda x: x)
        assert r.html == "<blockquote>\n<p>foo\nbar</p>\n</blockquote>"

    def test_lazy_continuation(self) -> None:
        r = parse_blocks("> foo\nbar", lambda x: x)
        assert r.html == "<blockquote>\n<p>foo\nbar</p>\n</blockquote>"

    def test_nested_blockquotes(self) -> None:
        r = parse_blocks("> > nested", lambda x: x)
        assert r.html == ("<blockquote>\n<blockquote>\n<p>nested</p>\n</blockquote>\n</blockquote>")

    def test_optional_space_after_marker(self) -> None:
        r = parse_blocks(">foo", lambda x: x)
        assert r.html == "<blockquote>\n<p>foo</p>\n</blockquote>"

    def test_blockquote_after_paragraph(self) -> None:
        r = parse_blocks("a\n\n> b", lambda x: x)
        assert r.html == "<p>a</p>\n<blockquote>\n<p>b</p>\n</blockquote>"

    def test_indented_blockquote_marker_not_recognized(self) -> None:
        r = parse_blocks("    > foo", lambda x: x)
        assert "> foo" in r.html
