from __future__ import annotations

import pytest

from webcompy.template._markdown_default import DefaultMarkdownParser


@pytest.fixture
def parser() -> DefaultMarkdownParser:
    return DefaultMarkdownParser()


class TestDefaultMarkdownParser:
    def test_headings_with_and_without_space(self, parser: DefaultMarkdownParser):
        source = "\n".join(
            [
                "# One",
                "##Two",
                "### Three",
                "####Four",
                "##### Five",
                "######Six",
            ]
        )
        assert parser.render(source) == ("<h1>One</h1><h2>Two</h2><h3>Three</h3><h4>Four</h4><h5>Five</h5><h6>Six</h6>")

    def test_paragraphs_join_lines_and_apply_inline_formatting(self, parser: DefaultMarkdownParser):
        source = "first line\nsecond line with **bold** and *italic*"
        assert parser.render(source) == "<p>first line second line with <strong>bold</strong> and <em>italic</em></p>"

    def test_unordered_lists_accept_both_markers(self, parser: DefaultMarkdownParser):
        source = "- one\n* two\n- three"
        assert parser.render(source) == "<ul><li>one</li><li>two</li><li>three</li></ul>"

    def test_ordered_lists_accept_both_markers(self, parser: DefaultMarkdownParser):
        source = "1. first\n2) second\n3. third"
        assert parser.render(source) == "<ol><li>first</li><li>second</li><li>third</li></ol>"

    def test_nested_lists_are_inside_parent_list_items(self, parser: DefaultMarkdownParser):
        source = "- parent\n  1. child\n     * grandchild"
        assert parser.render(source) == ("<ul><li>parent<ol><li>child<ul><li>grandchild</li></ul></li></ol></li></ul>")

    def test_deeply_nested_lists_support_alternate_markers(self, parser: DefaultMarkdownParser):
        source = "* level one\n  - level two\n    1) level three\n      * level four"
        assert parser.render(source) == (
            "<ul><li>level one<ul><li>level two<ol><li>level three"
            "<ul><li>level four</li></ul></li></ol></li></ul></li></ul>"
        )

    def test_fenced_code_blocks_ignore_language_and_escape_content(self, parser: DefaultMarkdownParser):
        source = '```python\nif x < 2:\n    print("ok")\n```'
        assert parser.render(source) == ("<pre><code>if x &lt; 2:\n    print(&quot;ok&quot;)</code></pre>")

    def test_inline_code_is_escaped(self, parser: DefaultMarkdownParser):
        assert parser.render("Use `<tag>&` here.") == "<p>Use <code>&lt;tag&gt;&amp;</code> here.</p>"

    def test_bold_before_italic(self, parser: DefaultMarkdownParser):
        assert parser.render("**bold** and *italic*") == "<p><strong>bold</strong> and <em>italic</em></p>"

    def test_strikethrough(self, parser: DefaultMarkdownParser):
        assert parser.render("~~removed~~") == "<p><del>removed</del></p>"

    def test_links(self, parser: DefaultMarkdownParser):
        assert parser.render("[WebComPy](https://example.com)") == ('<p><a href="https://example.com">WebComPy</a></p>')

    def test_images(self, parser: DefaultMarkdownParser):
        assert parser.render("![Logo](https://example.com/logo.png)") == (
            '<p><img src="https://example.com/logo.png" alt="Logo"></p>'
        )

    @pytest.mark.parametrize("rule", ["---", "***", "___"])
    def test_horizontal_rules(self, parser: DefaultMarkdownParser, rule: str):
        assert parser.render(rule) == "<hr>"

    def test_multiline_blockquotes_join_lines(self, parser: DefaultMarkdownParser):
        source = "> first line\n> second line"
        assert parser.render(source) == "<blockquote>first line second line</blockquote>"

    def test_html_blocks_are_passthrough(self, parser: DefaultMarkdownParser):
        assert parser.render("<div><span>raw</span></div>") == "<div><span>raw</span></div>"
        assert parser.render("<span>raw</span>") == "<span>raw</span>"
        assert parser.render('<user-card title="Hello" />') == '<user-card title="Hello" />'

    def test_multiline_self_closing_tag_is_preserved(self, parser: DefaultMarkdownParser):
        source = '<user-card\n  title="Hello"\n/>'
        assert parser.render(source) == source

    def test_multiline_self_closing_tag_with_attr_on_closing_line(self, parser: DefaultMarkdownParser):
        source = '<user-card\n  title="Hello" />\n'
        assert parser.render(source) == source.rstrip()

    def test_nested_self_closing_tag_does_not_prematurely_close_block(self, parser: DefaultMarkdownParser):
        source = "<div>\n  <span />\n  text\n</div>"
        assert parser.render(source) == source

    def test_multiline_closing_tag_block_is_preserved(self, parser: DefaultMarkdownParser):
        source = '<div\n  class="x">\ncontent\n</div>'
        assert parser.render(source) == source

    def test_template_syntax_is_preserved(self, parser: DefaultMarkdownParser):
        source = "Hello {{ name }}\n\n{% if visible %}Visible{% endif %}"
        assert parser.render(source) == ("<p>Hello {{ name }}</p><p>{% if visible %}Visible{% endif %}</p>")

    def test_mixed_content(self, parser: DefaultMarkdownParser):
        source = "# Title\n\nA **paragraph**.\n\n- parent\n  - child\n\n> quoted\n> text\n\n```\n<code>\n```"
        assert parser.render(source) == (
            "<h1>Title</h1><p>A <strong>paragraph</strong>.</p>"
            "<ul><li>parent<ul><li>child</li></ul></li></ul>"
            "<blockquote>quoted text</blockquote>"
            "<pre><code>&lt;code&gt;</code></pre>"
        )

    def test_source_is_dedented_and_tabs_use_two_spaces_for_lists(self, parser: DefaultMarkdownParser):
        source = """
            - parent
            \t- child
        """
        assert parser.render(source) == "<ul><li>parent<ul><li>child</li></ul></li></ul>"
