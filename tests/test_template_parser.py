from __future__ import annotations

import pytest

from webcompy.exception import WebComPyException
from webcompy.template._ast import (
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
        assert attr.is_boolean is True
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
