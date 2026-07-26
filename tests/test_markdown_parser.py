from __future__ import annotations

import pytest

from webcompy.template._markdown_default import DefaultMarkdownParser


@pytest.fixture
def parser() -> DefaultMarkdownParser:
    return DefaultMarkdownParser()


class TestDefaultMarkdownParser:
    def test_inline_code_is_escaped(self, parser: DefaultMarkdownParser):
        assert parser.render("Use `<tag>&` here.") == ("<p>Use <code>&lt;tag&gt;&amp;</code> here.</p>")

    def test_bold_before_italic(self, parser: DefaultMarkdownParser):
        assert parser.render("**bold** and *italic*") == ("<p><strong>bold</strong> and <em>italic</em></p>")

    def test_strikethrough(self, parser: DefaultMarkdownParser):
        assert parser.render("~~removed~~") == "<p><del>removed</del></p>"

    def test_links(self, parser: DefaultMarkdownParser):
        assert parser.render("[WebComPy](https://example.com)") == ('<p><a href="https://example.com">WebComPy</a></p>')

    def test_images(self, parser: DefaultMarkdownParser):
        assert parser.render("![Logo](https://example.com/logo.png)") == (
            '<p><img src="https://example.com/logo.png" alt="Logo"></p>'
        )

    @pytest.mark.parametrize("rule", ["---", "***", "___", "* * *", "- - -"])
    def test_horizontal_rules(self, parser: DefaultMarkdownParser, rule: str):
        assert parser.render(rule) == "<hr />"

    def test_type_6_html_block_single_line(self, parser: DefaultMarkdownParser):
        assert parser.render("<div></div>") == "<div></div>"

    def test_type_7_complete_open_tag_with_content(self, parser: DefaultMarkdownParser):
        assert parser.render('<user-card title="Hello" />') == ('<user-card title="Hello" />')

    def test_type_1_pre_block_multiline(self, parser: DefaultMarkdownParser):
        source = '<div\n  class="x">\ncontent\n</div>'
        assert parser.render(source) == source

    def test_template_syntax_is_preserved(self, parser: DefaultMarkdownParser):
        source = "Hello {{ name }}\n\n{% if visible %}Visible{% endif %}"
        assert parser.render(source) == ("<p>Hello {{ name }}</p>\n<p>{% if visible %}Visible{% endif %}</p>")

    def test_mixed_content(self, parser: DefaultMarkdownParser):
        source = "# Title\n\nA **paragraph**.\n\n- parent\n  - child\n\n> quoted\n> text\n\n```\n<code>\n```"
        assert parser.render(source) == (
            "<h1>Title</h1>\n"
            "<p>A <strong>paragraph</strong>.</p>\n"
            "<ul>\n<li>parent\n<ul>\n<li>child</li>\n</ul>\n</li>\n</ul>\n"
            "<blockquote>\n<p>quoted\ntext</p>\n</blockquote>\n"
            "<pre><code>&lt;code&gt;\n</code></pre>"
        )

    def test_multiline_self_closing_user_card(self, parser: DefaultMarkdownParser):
        result = parser.render('<user-card\n  title="Hello"\n/>')
        assert "&lt;user-card" in result

    def test_inline_open_tag_inline_content_with_attrs(self, parser: DefaultMarkdownParser):
        result = parser.render('<user-card\n  title="Hello" />\n')
        assert "&lt;user-card" in result


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
        assert result == "<ul>\n<li>one</li>\n<li>two</li>\n</ul>"

    def test_ordered_list_start(self, parser: DefaultMarkdownParser):
        result = parser.render("3. three\n4. four")
        assert result == '<ol start="3">\n<li>three</li>\n<li>four</li>\n</ol>'

    def test_ordered_list_default_start(self, parser: DefaultMarkdownParser):
        result = parser.render("1. one\n2. two")
        assert result == "<ol>\n<li>one</li>\n<li>two</li>\n</ol>"

    def test_multi_line_list_item(self, parser: DefaultMarkdownParser):
        result = parser.render("- foo\n  bar")
        assert "<li>foo\nbar</li>" in result

    def test_spaced_horizontal_rule_star(self, parser: DefaultMarkdownParser):
        result = parser.render("* * *")
        assert "<hr />" in result

    def test_spaced_horizontal_rule_dash(self, parser: DefaultMarkdownParser):
        result = parser.render("- - -")
        assert "<hr />" in result

    def test_spaced_horizontal_rule_underscore(self, parser: DefaultMarkdownParser):
        result = parser.render("_ _ _")
        assert "<hr />" in result

    def test_compact_horizontal_rule(self, parser: DefaultMarkdownParser):
        result = parser.render("---")
        assert result == "<hr />"

    def test_nested_lists_inside_parent_items(self, parser: DefaultMarkdownParser):
        result = parser.render("- parent\n  - child")
        assert result == "<ul>\n<li>parent\n<ul>\n<li>child</li>\n</ul>\n</li>\n</ul>"

    def test_three_bullet_markers_produce_separate_lists(self, parser: DefaultMarkdownParser):
        result = parser.render("- a\n+ b\n- c")
        assert result.count("<ul>") == 3

    def test_numbered_marker_too_large_not_a_list(self, parser: DefaultMarkdownParser):
        result = parser.render("1234567890. a")
        assert "<ol" not in result

    def test_empty_bullet_at_eol_cannot_interrupt_paragraph(self, parser: DefaultMarkdownParser):
        result = parser.render("paragraph\n- x")
        assert "<h2>" not in result
