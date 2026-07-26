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
    def test_parser_does_not_dedent(self) -> None:
        r = parse_blocks("    foo", lambda x: x)
        assert r.html == "<pre><code>foo\n</code></pre>"

    def test_multiline_indented_code_preserved(self) -> None:
        source = "    foo\n    bar"
        r = parse_blocks(source, lambda x: x)
        assert r.html == "<pre><code>foo\nbar\n</code></pre>"


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
        assert "<pre><code>" in r.html


class TestATXHeading:
    def test_h1_through_h6(self) -> None:
        for i in range(1, 7):
            r = parse_blocks("#" * i + " Title", lambda x: x)
            assert r.html == f"<h{i}>Title</h{i}>"

    def test_space_required(self) -> None:
        r = parse_blocks("#hashtag", lambda x: x)
        assert r.html == "<p>#hashtag</p>"

    def test_seven_hashes_not_heading(self) -> None:
        r = parse_blocks("####### foo", lambda x: x)
        assert r.html == "<p>####### foo</p>"

    def test_closing_hashes_stripped(self) -> None:
        r = parse_blocks("## Title ##", lambda x: x)
        assert r.html == "<h2>Title</h2>"

    def test_trailing_whitespace_stripped(self) -> None:
        r = parse_blocks("# foo   ", lambda x: x)
        assert r.html == "<h1>foo</h1>"

    def test_empty_heading(self) -> None:
        r = parse_blocks("#", lambda x: x)
        assert r.html == "<h1></h1>"


class TestSetextHeading:
    def test_h1_via_equals(self) -> None:
        r = parse_blocks("Title\n===", lambda x: x)
        assert r.html == "<h1>Title</h1>"

    def test_h2_via_dashes(self) -> None:
        r = parse_blocks("Title\n---", lambda x: x)
        assert r.html == "<h2>Title</h2>"

    def test_multi_line_setext(self) -> None:
        r = parse_blocks("Foo\nbar\n---", lambda x: x)
        assert r.html == "<h2>Foo\nbar</h2>"

    def test_setext_not_thematic_break(self) -> None:
        r = parse_blocks("Title\n---", lambda x: x)
        assert r.html == "<h2>Title</h2>"
        assert "<hr" not in r.html


class TestThematicBreak:
    @pytest.mark.parametrize("rule", ["---", "***", "___", "* * *", "- - -", "_ _ _"])
    def test_thematic_break_variants(self, rule: str) -> None:
        r = parse_blocks(rule, lambda x: x)
        assert r.html == "<hr />"

    def test_thematic_break_between_paragraphs(self) -> None:
        r = parse_blocks("a\n\n---\n\nb", lambda x: x)
        assert r.html == "<p>a</p>\n<hr />\n<p>b</p>"


class TestList:
    def test_simple_bullet(self) -> None:
        r = parse_blocks("- one\n- two", lambda x: x)
        assert r.html == "<ul>\n<li>one</li>\n<li>two</li>\n</ul>"

    def test_three_bullet_markers_separate_lists(self) -> None:
        r = parse_blocks("* a\n+ b\n- c", lambda x: x)
        assert r.html == "<ul>\n<li>a</li>\n</ul>\n<ul>\n<li>b</li>\n</ul>\n<ul>\n<li>c</li>\n</ul>"

    def test_ordered_dot_delimiter(self) -> None:
        r = parse_blocks("1. a\n2. b", lambda x: x)
        assert r.html == "<ol>\n<li>a</li>\n<li>b</li>\n</ol>"

    def test_ordered_paren_delimiter(self) -> None:
        r = parse_blocks("1) a\n2) b", lambda x: x)
        assert r.html == "<ol>\n<li>a</li>\n<li>b</li>\n</ol>"

    def test_ordered_start_attribute(self) -> None:
        r = parse_blocks("3. a\n4. b", lambda x: x)
        assert r.html == '<ol start="3">\n<li>a</li>\n<li>b</li>\n</ol>'

    def test_tight_list_no_p_wrappers(self) -> None:
        r = parse_blocks("- one\n- two", lambda x: x)
        assert "<p>" not in r.html

    def test_loose_list_wraps_paragraphs(self) -> None:
        r = parse_blocks("- one\n\n- two", lambda x: x)
        assert "<p>one</p>" in r.html
        assert "<p>two</p>" in r.html

    def test_nested_list_in_tight_item(self) -> None:
        r = parse_blocks("- parent\n  - child", lambda x: x)
        assert r.html == ("<ul>\n<li>parent\n<ul>\n<li>child</li>\n</ul>\n</li>\n</ul>")

    def test_list_in_block_quote(self) -> None:
        r = parse_blocks("> - list", lambda x: x)
        assert r.html == "<blockquote>\n<ul>\n<li>list</li>\n</ul>\n</blockquote>"

    def test_extra_spaces_after_marker(self) -> None:
        r = parse_blocks("-    extra", lambda x: x)
        assert "extra" in r.html

    def test_numbered_marker_too_large_not_a_list(self) -> None:
        r = parse_blocks("1234567890. a", lambda x: x)
        assert r.html == "<p>1234567890. a</p>"

    def test_dash_then_blank_does_not_interrupt_paragraph(self) -> None:
        r = parse_blocks("paragraph\n- x", lambda x: x)
        assert "<h2>" not in r.html
