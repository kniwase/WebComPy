from __future__ import annotations

import pytest

from webcompy.template._markdown_default import DefaultMarkdownParser


@pytest.fixture
def parser() -> DefaultMarkdownParser:
    return DefaultMarkdownParser()


class TestDefaultMarkdownParser:
    @pytest.mark.gfm_deviation
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

    @pytest.mark.gfm_deviation
    def test_paragraphs_join_lines_and_apply_inline_formatting(self, parser: DefaultMarkdownParser):
        source = "first line\nsecond line with **bold** and *italic*"
        assert parser.render(source) == "<p>first line second line with <strong>bold</strong> and <em>italic</em></p>"

    @pytest.mark.gfm_deviation
    def test_unordered_lists_accept_both_markers(self, parser: DefaultMarkdownParser):
        source = "- one\n* two\n- three"
        assert parser.render(source) == "<ul><li>one</li><li>two</li><li>three</li></ul>"

    @pytest.mark.gfm_deviation
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

    @pytest.mark.gfm_deviation
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

    @pytest.mark.gfm_deviation
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

    @pytest.mark.gfm_deviation
    def test_source_is_dedented_and_tabs_use_two_spaces_for_lists(self, parser: DefaultMarkdownParser):
        source = """
            - parent
            \t- child
        """
        assert parser.render(source) == "<ul><li>parent<ul><li>child</li></ul></li></ul>"


class TestMarkdownCodeBlockTemplateProtection:
    def test_hole_in_code_block_rendered_literally(self, parser: DefaultMarkdownParser):
        result = parser.render("```\n{{ x }}\n```")
        assert "\x00" in result
        assert "x }}" in result
        assert "{{ x }}" not in result

    def test_directive_in_code_block_preserved(self, parser: DefaultMarkdownParser):
        result = parser.render("```\n{% if y %}text{% endif %}\n```")
        assert "% if y %}" in result
        assert "% endif %}" in result
        assert "\x00" in result

    def test_hole_in_inline_code_span(self, parser: DefaultMarkdownParser):
        result = parser.render("Hello `{{ x }}` world")
        assert "<code>" in result
        assert "x }}</code>" in result
        assert "{{ x }}" not in result


class TestMarkdownInlineTokenization:
    def test_italic_containing_bold(self, parser: DefaultMarkdownParser):
        result = parser.render("*a **b** c*")
        assert result == "<p><em>a <strong>b</strong> c</em></p>"

    def test_strikethrough_containing_bold(self, parser: DefaultMarkdownParser):
        result = parser.render("~~a **b** c~~")
        assert result == "<p><del>a <strong>b</strong> c</del></p>"

    def test_no_placeholder_leak(self, parser: DefaultMarkdownParser):
        result = parser.render("*a **b** c*")
        assert "__WEBCOMPY_INLINE_" not in result
        assert "\x00WC" not in result

    def test_user_text_placeholder_like_preserved(self, parser: DefaultMarkdownParser):
        result = parser.render("__WEBCOMPY_INLINE_0__ and **bold**")
        assert "__WEBCOMPY_INLINE_0__" in result
        assert "<strong>bold</strong>" in result


class TestMarkdownUrlAllowList:
    def test_javascript_url_neutralized(self, parser: DefaultMarkdownParser):
        result = parser.render("[click](javascript:alert(1))")
        assert "javascript:" not in result
        assert "<a" not in result
        assert "click" in result

    def test_vbscript_url_neutralized(self, parser: DefaultMarkdownParser):
        result = parser.render("[click](vbscript:msgbox)")
        assert "vbscript:" not in result
        assert "<a" not in result

    def test_data_url_neutralized(self, parser: DefaultMarkdownParser):
        result = parser.render("[click](data:text/html,evil)")
        assert "data:" not in result
        assert "<a" not in result

    def test_https_url_allowed(self, parser: DefaultMarkdownParser):
        result = parser.render("[click](https://example.com)")
        assert '<a href="https://example.com">click</a>' in result

    def test_http_url_allowed(self, parser: DefaultMarkdownParser):
        result = parser.render("[click](http://example.com)")
        assert '<a href="http://example.com">click</a>' in result

    def test_mailto_url_allowed(self, parser: DefaultMarkdownParser):
        result = parser.render("[mail](mailto:foo@example.com)")
        assert '<a href="mailto:foo@example.com">mail</a>' in result

    def test_relative_url_allowed(self, parser: DefaultMarkdownParser):
        result = parser.render("[docs](/docs)")
        assert '<a href="/docs">docs</a>' in result

    def test_fragment_url_allowed(self, parser: DefaultMarkdownParser):
        result = parser.render("[section](#section)")
        assert '<a href="#section">section</a>' in result

    def test_image_javascript_neutralized(self, parser: DefaultMarkdownParser):
        result = parser.render("![alt](javascript:alert(1))")
        assert "javascript:" not in result
        assert "<img" not in result

    def test_link_with_leading_control_char_neutralized(self, parser: DefaultMarkdownParser):
        result = parser.render("[click](\x01javascript:alert(1))")
        assert "javascript:" not in result
        assert "<a" not in result
        assert "click" in result

    def test_image_with_leading_control_char_neutralized(self, parser: DefaultMarkdownParser):
        result = parser.render("![alt](\x02data:text/html,evil)")
        assert "data:" not in result
        assert "<img" not in result

    def test_link_with_del_control_char_neutralized(self, parser: DefaultMarkdownParser):
        result = parser.render("[click](\x7fhttps://example.com)")
        assert "\x7f" not in result
        assert "<a" not in result


class TestMarkdownLists:
    def test_plus_marker_list(self, parser: DefaultMarkdownParser):
        result = parser.render("+ one\n+ two")
        assert result == "<ul><li>one</li><li>two</li></ul>"

    def test_ordered_list_start(self, parser: DefaultMarkdownParser):
        result = parser.render("3. three\n4. four")
        assert result == '<ol start="3"><li>three</li><li>four</li></ol>'

    def test_ordered_list_default_start(self, parser: DefaultMarkdownParser):
        result = parser.render("1. one\n2. two")
        assert result == "<ol><li>one</li><li>two</li></ol>"

    def test_multi_line_list_item(self, parser: DefaultMarkdownParser):
        result = parser.render("- foo\n  bar")
        assert "<li>foo bar</li>" in result

    def test_spaced_horizontal_rule_star(self, parser: DefaultMarkdownParser):
        result = parser.render("* * *")
        assert "<hr>" in result

    def test_spaced_horizontal_rule_dash(self, parser: DefaultMarkdownParser):
        result = parser.render("- - -")
        assert "<hr>" in result

    def test_spaced_horizontal_rule_underscore(self, parser: DefaultMarkdownParser):
        result = parser.render("_ _ _")
        assert "<hr>" in result

    def test_compact_horizontal_rule(self, parser: DefaultMarkdownParser):
        result = parser.render("---")
        assert "<hr>" in result
