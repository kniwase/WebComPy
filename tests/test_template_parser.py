from __future__ import annotations

import pytest

from webcompy.exception import WebComPyException
from webcompy.template._ast import (
    ForNode,
    IfNode,
    TemplateElement,
    TemplateText,
)
from webcompy.template._holes import Hole, LiteralText
from webcompy.template._parser import (
    REJECTED_TAGS,
    VOID_ELEMENTS,
    parse_template,
)


def _parse(source: str) -> list:
    return parse_template(source)


class TestBasicStructure:
    def test_simple_div(self):
        roots = _parse("<div></div>")
        assert len(roots) == 1
        assert isinstance(roots[0], TemplateElement)
        assert roots[0].tag_name == "div"
        assert roots[0].children == []

    def test_nested_elements(self):
        roots = _parse("<div><p>Hello</p></div>")
        assert len(roots) == 1
        div = roots[0]
        assert div.tag_name == "div"
        assert len(div.children) == 1
        p = div.children[0]
        assert isinstance(p, TemplateElement)
        assert p.tag_name == "p"
        assert len(p.children) == 1
        text = p.children[0]
        assert isinstance(text, TemplateText)
        assert text.parts == [LiteralText("Hello")]

    def test_multiple_root_elements(self):
        roots = _parse("<div></div><span></span>")
        assert len(roots) == 2
        assert roots[0].tag_name == "div"
        assert roots[1].tag_name == "span"

    def test_text_with_inline_element(self):
        roots = _parse("<p>Hello <strong>world</strong>!</p>")
        p = roots[0]
        assert len(p.children) == 3
        assert p.children[0] == TemplateText(parts=[LiteralText("Hello ")])
        assert isinstance(p.children[1], TemplateElement)
        assert p.children[1].tag_name == "strong"
        assert p.children[2] == TemplateText(parts=[LiteralText("!")])

    def test_attributes(self):
        roots = _parse('<a href="https://example.com" target="_blank">link</a>')
        a = roots[0]
        assert a.tag_name == "a"
        assert len(a.attrs) == 2
        attr_names = {attr.name for attr in a.attrs}
        assert attr_names == {"href", "target"}
        href_attr = next(attr for attr in a.attrs if attr.name == "href")
        assert href_attr.value == [LiteralText("https://example.com")]
        assert not href_attr.is_boolean


class TestVoidElements:
    def test_br_is_void(self):
        assert "br" in VOID_ELEMENTS

    def test_img_is_void(self):
        assert "img" in VOID_ELEMENTS

    def test_input_is_void(self):
        assert "input" in VOID_ELEMENTS

    def test_div_is_not_void(self):
        assert "div" not in VOID_ELEMENTS

    def test_br_does_not_push_to_stack(self):
        roots = _parse("<div><br></div>")
        div = roots[0]
        assert len(div.children) == 1
        br = div.children[0]
        assert isinstance(br, TemplateElement)
        assert br.tag_name == "br"
        assert br.children == []

    def test_br_preserves_tag_name_for_binder(self):
        roots = _parse("<br>")
        assert roots[0].tag_name == "br"

    def test_img_with_attributes(self):
        roots = _parse('<img src="/x.png" alt="x">')
        assert len(roots) == 1
        img = roots[0]
        assert img.tag_name == "img"
        assert len(img.attrs) == 2

    def test_void_inside_text(self):
        roots = _parse("<div>text<br>more</div>")
        div = roots[0]
        assert len(div.children) == 3
        assert isinstance(div.children[0], TemplateText)
        assert isinstance(div.children[1], TemplateElement)
        assert div.children[1].tag_name == "br"
        assert isinstance(div.children[2], TemplateText)


class TestSelfClosingTags:
    def test_self_closing_img(self):
        roots = _parse('<img src="/x.png" />')
        assert len(roots) == 1
        img = roots[0]
        assert img.tag_name == "img"
        assert len(img.attrs) == 1

    def test_self_closing_div(self):
        roots = _parse("<div />")
        assert len(roots) == 1
        div = roots[0]
        assert div.tag_name == "div"
        assert div.children == []

    def test_self_closing_then_sibling(self):
        roots = _parse("<br /><span>after</span>")
        assert len(roots) == 2
        assert roots[0].tag_name == "br"
        assert roots[1].tag_name == "span"


class TestBooleanAttributes:
    def test_bare_boolean_attr(self):
        roots = _parse("<input disabled>")
        assert roots[0].attrs[0].name == "disabled"
        assert roots[0].attrs[0].is_boolean is True
        assert roots[0].attrs[0].value == []

    def test_empty_value_boolean(self):
        roots = _parse('<input disabled="">')
        attr = roots[0].attrs[0]
        assert attr.name == "disabled"
        assert attr.is_boolean is False
        assert attr.value == []

    def test_explicit_string_value(self):
        roots = _parse('<input disabled="disabled">')
        attr = roots[0].attrs[0]
        assert attr.is_boolean is False
        assert attr.value == [LiteralText("disabled")]

    def test_checked_boolean(self):
        roots = _parse('<input type="checkbox" checked>')
        assert len(roots[0].attrs) == 2
        checked = next(a for a in roots[0].attrs if a.name == "checked")
        assert checked.is_boolean is True


class TestComments:
    def test_comment_is_skipped(self):
        roots = _parse("<!-- this is a comment --><div></div>")
        assert len(roots) == 1
        assert roots[0].tag_name == "div"

    def test_comment_inside_element(self):
        roots = _parse("<div><!-- comment --><span>x</span></div>")
        div = roots[0]
        assert len(div.children) == 1
        assert div.children[0].tag_name == "span"

    def test_multiple_comments(self):
        roots = _parse("<!-- one --><p>x</p><!-- two -->")
        assert len(roots) == 1
        assert roots[0].tag_name == "p"

    def test_html_comment_with_content(self):
        roots = _parse("<div><!-- <not-a-tag> text --></div>")
        assert len(roots[0].children) == 0


class TestRejectedTags:
    @pytest.mark.parametrize("tag", sorted(REJECTED_TAGS))
    def test_rejected_tag_raises(self, tag):
        with pytest.raises(WebComPyException, match=tag):
            _parse(f"<{tag}>content</{tag}>")

    def test_script_with_interpolation_still_rejected(self):
        with pytest.raises(WebComPyException, match="script"):
            _parse("<script>{{ data }}</script>")

    def test_style_rejected_with_message(self):
        with pytest.raises(WebComPyException):
            _parse("<style>body { color: red; }</style>")

    def test_self_closing_rejected_tag(self):
        with pytest.raises(WebComPyException):
            _parse("<script />")


class TestHoleScanningInAttributes:
    def test_single_hole_in_attr(self):
        roots = _parse('<p class="{{ cls }}"></p>')
        attr = roots[0].attrs[0]
        assert attr.value == [Hole("cls")]

    def test_mixed_literal_and_hole_in_attr(self):
        roots = _parse('<p class="card {{ cls }}"></p>')
        attr = roots[0].attrs[0]
        assert attr.value == [LiteralText("card "), Hole("cls")]

    def test_multiple_holes_in_attr(self):
        roots = _parse('<p data-a="{{ a }}" data-b="{{ b }}"></p>')
        a = roots[0].attrs[0]
        b = roots[0].attrs[1]
        assert a.value == [Hole("a")]
        assert b.value == [Hole("b")]

    def test_dotted_path_in_attr(self):
        roots = _parse('<p class="{{ user.name }}"></p>')
        attr = roots[0].attrs[0]
        assert attr.value == [Hole("user.name")]

    def test_holes_in_text_content(self):
        roots = _parse("<p>Hello {{ name }}, count: {{ count }}</p>")
        text = roots[0].children[0]
        assert isinstance(text, TemplateText)
        assert text.parts == [
            LiteralText("Hello "),
            Hole("name"),
            LiteralText(", count: "),
            Hole("count"),
        ]

    def test_literal_only_text(self):
        roots = _parse("<p>just text</p>")
        text = roots[0].children[0]
        assert text.parts == [LiteralText("just text")]


class TestLenientUnknownTags:
    def test_unknown_tag_creates_element(self):
        roots = _parse("<widget>x</widget>")
        assert len(roots) == 1
        assert roots[0].tag_name == "widget"

    def test_case_normalized_to_lower(self):
        roots = _parse("<DIV></DIV>")
        assert roots[0].tag_name == "div"

    def test_uppercase_void(self):
        roots = _parse("<BR>")
        assert roots[0].tag_name == "br"


class TestIfDirectiveParsing:
    def test_simple_if(self):
        roots = _parse("<div>{% if show %}A{% endif %}</div>")
        div = roots[0]
        assert len(div.children) == 1
        if_node = div.children[0]
        assert isinstance(if_node, IfNode)
        assert len(if_node.branches) == 1
        cond, body = if_node.branches[0]
        assert cond == "show"
        assert len(body) == 1
        assert isinstance(body[0], TemplateText)
        assert body[0].parts == [LiteralText("A")]

    def test_if_with_surrounding_literal_text(self):
        roots = _parse("<div>before{% if x %}IN{% endif %}after</div>")
        div = roots[0]
        assert len(div.children) == 3
        assert isinstance(div.children[0], TemplateText)
        assert div.children[0].parts == [LiteralText("before")]
        assert isinstance(div.children[1], IfNode)
        assert isinstance(div.children[2], TemplateText)
        assert div.children[2].parts == [LiteralText("after")]

    def test_if_with_element_body(self):
        roots = _parse("{% if x %}<p>hi</p>{% endif %}")
        assert len(roots) == 1
        if_node = roots[0]
        assert isinstance(if_node, IfNode)
        cond, body = if_node.branches[0]
        assert cond == "x"
        assert len(body) == 1
        assert isinstance(body[0], TemplateElement)
        assert body[0].tag_name == "p"

    def test_if_with_hole_in_condition_text(self):
        roots = _parse("{% if show %}Hello {{ name }}{% endif %}")
        if_node = roots[0]
        assert isinstance(if_node, IfNode)
        body = if_node.branches[0][1]
        text = body[0]
        assert isinstance(text, TemplateText)
        assert text.parts == [LiteralText("Hello "), Hole("name")]

    def test_if_else_chain(self):
        roots = _parse("{% if a %}A{% else %}B{% endif %}")
        if_node = roots[0]
        assert isinstance(if_node, IfNode)
        assert len(if_node.branches) == 2
        assert if_node.branches[0][0] == "a"
        assert if_node.branches[1][0] is None

    def test_if_elif_else_chain(self):
        roots = _parse("{% if a %}A{% elif b %}B{% else %}C{% endif %}")
        if_node = roots[0]
        assert isinstance(if_node, IfNode)
        assert len(if_node.branches) == 3
        assert if_node.branches[0][0] == "a"
        assert if_node.branches[1][0] == "b"
        assert if_node.branches[2][0] is None

    def test_if_with_dot_notation(self):
        roots = _parse("{% if item.visible %}A{% endif %}")
        if_node = roots[0]
        assert if_node.branches[0][0] == "item.visible"


class TestForDirectiveParsing:
    def test_simple_for(self):
        roots = _parse("{% for item in items %}<p>{{ item }}</p>{% endfor %}")
        assert len(roots) == 1
        for_node = roots[0]
        assert isinstance(for_node, ForNode)
        assert for_node.loop_vars == ["item"]
        assert for_node.iterable_path == "items"
        assert len(for_node.body) == 1
        p = for_node.body[0]
        assert isinstance(p, TemplateElement)
        assert p.tag_name == "p"

    def test_for_with_dict_unpacking(self):
        roots = _parse("{% for key, value in my_dict %}<p>{{ key }}: {{ value }}</p>{% endfor %}")
        for_node = roots[0]
        assert isinstance(for_node, ForNode)
        assert for_node.loop_vars == ["key", "value"]
        assert for_node.iterable_path == "my_dict"

    def test_for_with_whitespace(self):
        roots = _parse("{%   for   x   in   items   %}<p>{{ x }}</p>{%   endfor   %}")
        for_node = roots[0]
        assert for_node.loop_vars == ["x"]
        assert for_node.iterable_path == "items"

    def test_for_with_dot_notation(self):
        roots = _parse("{% for post in user.posts %}<p>{{ post }}</p>{% endfor %}")
        for_node = roots[0]
        assert for_node.iterable_path == "user.posts"

    def test_for_with_surrounding_text(self):
        roots = _parse("<div>before{% for x in y %}<b>x</b>{% endfor %}after</div>")
        div = roots[0]
        assert len(div.children) == 3
        assert isinstance(div.children[0], TemplateText)
        assert isinstance(div.children[1], ForNode)
        assert isinstance(div.children[2], TemplateText)


class TestNestedControlFlowParsing:
    def test_if_inside_for(self):
        roots = _parse("{% for item in items %}{% if item.visible %}<li>{{ item.name }}</li>{% endif %}{% endfor %}")
        for_node = roots[0]
        assert isinstance(for_node, ForNode)
        assert len(for_node.body) == 1
        if_node = for_node.body[0]
        assert isinstance(if_node, IfNode)
        assert if_node.branches[0][0] == "item.visible"
        li = if_node.branches[0][1][0]
        assert isinstance(li, TemplateElement)
        assert li.tag_name == "li"

    def test_for_inside_if(self):
        roots = _parse("{% if show %}<ul>{% for x in items %}<li>x</li>{% endfor %}</ul>{% endif %}")
        if_node = roots[0]
        assert isinstance(if_node, IfNode)
        ul = if_node.branches[0][1][0]
        assert isinstance(ul, TemplateElement)
        assert ul.tag_name == "ul"
        for_node = ul.children[0]
        assert isinstance(for_node, ForNode)

    def test_deeply_nested(self):
        roots = _parse(
            "<div>{% for x in xs %}{% if x.ok %}<p>{% for c in x.children %}<span>{{ c }}</span>{% endfor %}</p>{% endif %}{% endfor %}</div>"
        )
        div = roots[0]
        for_node = div.children[0]
        assert isinstance(for_node, ForNode)
        if_node = for_node.body[0]
        assert isinstance(if_node, IfNode)
        p = if_node.branches[0][1][0]
        assert isinstance(p, TemplateElement)
        inner_for = p.children[0]
        assert isinstance(inner_for, ForNode)
        assert inner_for.loop_vars == ["c"]
        assert inner_for.iterable_path == "x.children"


class TestMalformedControlFlowParsing:
    def test_missing_endif(self):
        with pytest.raises(WebComPyException, match="Unclosed"):
            _parse("{% if x %}A")

    def test_missing_endfor(self):
        with pytest.raises(WebComPyException, match="Unclosed"):
            _parse("{% for x in y %}A")

    def test_extra_endif(self):
        with pytest.raises(WebComPyException, match="endif"):
            _parse("A{% endif %}")

    def test_extra_endfor(self):
        with pytest.raises(WebComPyException, match="endfor"):
            _parse("A{% endfor %}")

    def test_mismatched_elif_without_if(self):
        with pytest.raises(WebComPyException, match="elif"):
            _parse("{% elif x %}A{% endif %}")

    def test_mismatched_else_without_if(self):
        with pytest.raises(WebComPyException, match="else"):
            _parse("{% else %}A{% endif %}")

    def test_for_endif_mismatch(self):
        with pytest.raises(WebComPyException, match="endif"):
            _parse("{% for x in y %}A{% endif %}")

    def test_if_endfor_mismatch(self):
        with pytest.raises(WebComPyException, match="endfor"):
            _parse("{% if x %}A{% endfor %}")

    def test_invalid_for_missing_in_separator(self):
        with pytest.raises(WebComPyException, match="in"):
            _parse("{% for x %}A{% endfor %}")

    def test_invalid_for_empty_loop_var(self):
        with pytest.raises(WebComPyException, match="loop variable"):
            _parse("{% for , in items %}A{% endfor %}")


class TestDirectivePatternEdgeCases:
    def test_if_surrounded_by_text_with_holes(self):
        roots = _parse("<p>a{{ x }}{% if y %}b{% endif %}c</p>")
        p = roots[0]
        assert len(p.children) == 3
        first = p.children[0]
        assert isinstance(first, TemplateText)
        assert first.parts == [LiteralText("a"), Hole("x")]
        assert isinstance(p.children[1], IfNode)
        assert isinstance(p.children[2], TemplateText)
        assert p.children[2].parts == [LiteralText("c")]


class TestMalformedHtmlErrors:
    def test_mismatched_closing_tag_raises(self):
        with pytest.raises(WebComPyException) as exc_info:
            parse_template("<div><b>bold</div></b>")
        msg = str(exc_info.value)
        assert "b" in msg
        assert "div" in msg

    def test_unclosed_element_raises(self):
        with pytest.raises(WebComPyException) as exc_info:
            parse_template("<div><p>hi")
        msg = str(exc_info.value)
        assert "p" in msg
        assert "div" in msg

    def test_stray_closing_tag_raises(self):
        with pytest.raises(WebComPyException) as exc_info:
            parse_template("<div>text</span></div>")
        msg = str(exc_info.value)
        assert "span" in msg

    def test_well_formed_template_passes(self):
        roots = parse_template("<div><p>hi</p></div>")
        assert len(roots) == 1
        assert roots[0].tag_name == "div"


class TestDirectiveParagraphStripping:
    def test_paragraph_with_only_if_directive_stripped(self):
        from webcompy.template import _strip_directive_paragraphs

        result = _strip_directive_paragraphs("<p>{% if x %}</p>")
        assert result == "{% if x %}"

    def test_paragraph_with_only_for_directive_stripped(self):
        from webcompy.template import _strip_directive_paragraphs

        result = _strip_directive_paragraphs("<p>{% for x in items %}</p>")
        assert result == "{% for x in items %}"

    def test_paragraph_with_text_preserved(self):
        from webcompy.template import _strip_directive_paragraphs

        original = "<p>{% if x %}text{% endif %}</p>"
        result = _strip_directive_paragraphs(original)
        assert result == original

    def test_paragraph_with_text_then_directive_preserved(self):
        from webcompy.template import _strip_directive_paragraphs

        original = "<p>before {% if x %}text{% endif %}</p>"
        result = _strip_directive_paragraphs(original)
        assert result == original

    def test_paragraph_with_only_endif_stripped(self):
        from webcompy.template import _strip_directive_paragraphs

        result = _strip_directive_paragraphs("<p>{% endif %}</p>")
        assert result == "{% endif %}"


class TestUnsupportedHoleExpression:
    def test_subscript_in_text_raises(self):
        with pytest.raises(WebComPyException) as exc_info:
            parse_template("<p>{{ items[0] }}</p>")
        msg = str(exc_info.value)
        assert "items[0]" in msg

    def test_call_in_text_raises(self):
        with pytest.raises(WebComPyException) as exc_info:
            parse_template("<p>{{ get_name() }}</p>")
        msg = str(exc_info.value)
        assert "get_name" in msg

    def test_valid_hole_still_works(self):
        roots = parse_template("<p>{{ name }}</p>")
        assert len(roots) == 1


class TestRcdataPinning:
    def test_textarea_markup_parsed_as_text(self):
        roots = parse_template("<div><textarea><b>x</b></textarea></div>")
        div = roots[0]
        textarea = div.children[0]
        assert textarea.tag_name == "textarea"
        assert len(textarea.children) == 1
        text_node = textarea.children[0]
        assert isinstance(text_node, TemplateText)
        assert text_node.parts[0].text == "<b>x</b>"

    def test_title_markup_parsed_as_text(self):
        roots = parse_template("<div><title><b>y</b></title></div>")
        title = roots[0].children[0]
        assert title.tag_name == "title"
        assert len(title.children) == 1
        text_node = title.children[0]
        assert isinstance(text_node, TemplateText)
        assert text_node.parts[0].text == "<b>y</b>"
