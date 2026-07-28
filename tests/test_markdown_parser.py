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
            '<p><img src="https://example.com/logo.png" alt="Logo" /></p>'
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
        assert "<user-card" in result
        assert "/>" in result

    def test_inline_open_tag_inline_content_with_attrs(self, parser: DefaultMarkdownParser):
        result = parser.render('<user-card\n  title="Hello" />\n')
        assert "<user-card" in result
        assert "/>" in result


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

    def test_directive_in_inline_code_span(self, parser: DefaultMarkdownParser):
        result = parser.render("before `{% if cond %}` after")
        assert "<code>" in result
        assert "{% if cond %}" in result or "\x00" in result

    def test_adjacent_code_spans_with_template_syntax(self, parser: DefaultMarkdownParser):
        result = parser.render("`{{ a }}` and `{{ b }}`")
        assert result.count("<code>") == 2

    def test_code_span_with_mixed_template_and_text(self, parser: DefaultMarkdownParser):
        result = parser.render("`prefix {{ hole }} suffix`")
        assert "<code>" in result
        assert "hole" in result or "\x00" in result


class TestMarkdownInlineTokenization:
    def test_italic_containing_bold(self, parser: DefaultMarkdownParser):
        result = parser.render("*a **b** c*")
        assert result == "<p><em>a <strong>b</strong> c</em></p>"

    def test_strikethrough_containing_bold(self, parser: DefaultMarkdownParser):
        result = parser.render("~~a **b** c~~")
        assert result == "<p><del>a <strong>b</strong> c</del></p>"

    def test_no_placeholder_leak(self, parser: DefaultMarkdownParser):
        result = parser.render("*a **b** c*")
        assert "\x00" not in result


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
        assert "\x01" not in result
        assert "%01" in result
        assert "click" in result

    def test_image_with_leading_control_char_neutralized(self, parser: DefaultMarkdownParser):
        result = parser.render("![alt](\x02data:text/html,evil)")
        assert "\x02" not in result
        assert "%02" in result
        assert "alt" in result

    def test_link_with_del_control_char_neutralized(self, parser: DefaultMarkdownParser):
        result = parser.render("[click](\x7fhttps://example.com)")
        assert "\x7f" not in result
        assert "%7F" in result


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


class TestExtendedAutolinkBoundaries:
    def test_autolink_after_code_span(self, parser: DefaultMarkdownParser):
        result = parser.render("`code` then www.example.com/x here")
        assert result == ('<p><code>code</code> then <a href="http://www.example.com/x">www.example.com/x</a> here</p>')

    def test_autolink_after_entity_reference(self, parser: DefaultMarkdownParser):
        result = parser.render("a &copy; www.example.com/x")
        assert result == ('<p>a \u00a9 <a href="http://www.example.com/x">www.example.com/x</a></p>')

    def test_autolink_after_inline_link(self, parser: DefaultMarkdownParser):
        result = parser.render("[a](b) www.example.com")
        assert '<a href="http://www.example.com">www.example.com</a>' in result

    def test_autolink_mid_text(self, parser: DefaultMarkdownParser):
        result = parser.render("see www.example.com/x for details")
        assert '<a href="http://www.example.com/x">www.example.com/x</a>' in result

    def test_no_autolink_after_letter(self, parser: DefaultMarkdownParser):
        result = parser.render("xwww.example.com")
        assert "<a " not in result

    def test_no_autolink_after_backtick_without_space(self, parser: DefaultMarkdownParser):
        result = parser.render("`c`www.example.com")
        assert "<a " not in result

    def test_no_extended_autolink_inside_failed_angle_bracket(self, parser: DefaultMarkdownParser):
        result = parser.render("< http://foo.bar >")
        assert "<a " not in result
        assert "&lt; http://foo.bar &gt;" in result

    def test_email_autolink_has_no_boundary_requirement(self, parser: DefaultMarkdownParser):
        result = parser.render("`c` then foo@bar.com end")
        assert '<a href="mailto:foo@bar.com">foo@bar.com</a>' in result


class TestExtendedAutolinkDomainUnderscoreRules:
    def test_underscore_in_third_to_last_segment_linked(self, parser: DefaultMarkdownParser):
        result = parser.render("www._xxx.yyy.zzz")
        assert '<a href="http://www._xxx.yyy.zzz">www._xxx.yyy.zzz</a>' in result

    def test_underscore_in_second_to_last_segment_not_linked(self, parser: DefaultMarkdownParser):
        result = parser.render("www.xxx._yyy.zzz")
        assert "<a " not in result

    def test_underscore_in_last_segment_not_linked(self, parser: DefaultMarkdownParser):
        result = parser.render("www.xxx.yyy._zzz")
        assert "<a " not in result

    def test_underscore_in_two_segment_domain_not_linked(self, parser: DefaultMarkdownParser):
        result = parser.render("www.xxx_yyy.zzz")
        assert "<a " not in result


class TestTagfilterAsymmetry:
    def test_type1_script_block_passes_raw(self, parser: DefaultMarkdownParser):
        result = parser.render("<script>\nalert(1)\n</script>")
        assert result == "<script>\nalert(1)\n</script>"

    def test_type1_style_block_passes_raw(self, parser: DefaultMarkdownParser):
        result = parser.render("<style>\nbody{color:red}\n</style>")
        assert result == "<style>\nbody{color:red}\n</style>"

    def test_type1_textarea_block_passes_raw(self, parser: DefaultMarkdownParser):
        result = parser.render("<textarea>x</textarea>")
        assert result == "<textarea>x</textarea>"

    def test_type7_iframe_block_filtered(self, parser: DefaultMarkdownParser):
        result = parser.render("<iframe src=x></iframe>")
        assert "&lt;iframe" in result

    def test_inline_disallowed_tag_filtered(self, parser: DefaultMarkdownParser):
        result = parser.render("a <script>x</script> b")
        assert "&lt;script>" in result

    def test_inline_title_tag_filtered(self, parser: DefaultMarkdownParser):
        result = parser.render("inline <title>t</title> here")
        assert "&lt;title>" in result


class TestMarkdownUriNormalization:
    def test_scheme_url_brackets_and_bang_percent_encoded(self, parser: DefaultMarkdownParser):
        result = parser.render("[a](https://example.com/[p]!)")
        assert '<a href="https://example.com/%5Bp%5D%21">' in result
