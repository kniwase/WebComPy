from __future__ import annotations

import pytest

from webcompy.components._css_utils import (
    _contains_top_level_ampersand,
    _insert_cid,
    _is_declaration_body_at_rule,
    _is_keyframes_rule,
    _scope_selector,
    _split_selector_parts,
)
from webcompy.exception import WebComPyException


class TestIsKeyframesRule:
    def test_basic_keyframes(self) -> None:
        assert _is_keyframes_rule("@keyframes spin") is True

    def test_vendor_webkit_keyframes(self) -> None:
        assert _is_keyframes_rule("@-webkit-keyframes spin") is True

    def test_vendor_moz_keyframes(self) -> None:
        assert _is_keyframes_rule("@-moz-keyframes spin") is True

    def test_vendor_o_keyframes(self) -> None:
        assert _is_keyframes_rule("@-o-keyframes spin") is True

    def test_case_insensitive(self) -> None:
        assert _is_keyframes_rule("@Keyframes spin") is True
        assert _is_keyframes_rule("@KEYFRAMES spin") is True

    def test_font_face_is_not_keyframes(self) -> None:
        assert _is_keyframes_rule("@font-face") is False

    def test_media_is_not_keyframes(self) -> None:
        assert _is_keyframes_rule("@media (max-width: 768px)") is False

    def test_stripped(self) -> None:
        assert _is_keyframes_rule("  @keyframes spin  ") is True


class TestIsDeclarationBodyAtRule:
    def test_font_face(self) -> None:
        assert _is_declaration_body_at_rule("@font-face") is True

    def test_page(self) -> None:
        assert _is_declaration_body_at_rule("@page") is True

    def test_property(self) -> None:
        assert _is_declaration_body_at_rule("@property --x") is True

    def test_counter_style(self) -> None:
        assert _is_declaration_body_at_rule("@counter-style x") is True

    def test_case_insensitive(self) -> None:
        assert _is_declaration_body_at_rule("@FONT-FACE") is True

    def test_keyframes_is_not_declaration_body(self) -> None:
        assert _is_declaration_body_at_rule("@keyframes spin") is False

    def test_media_is_not_declaration_body(self) -> None:
        assert _is_declaration_body_at_rule("@media (max-width: 768px)") is False

    def test_stripped(self) -> None:
        assert _is_declaration_body_at_rule("  @font-face  ") is True


class TestSplitSelectorParts:
    def test_single_compound(self) -> None:
        parts, combinators = _split_selector_parts(".x")
        assert parts == [".x"]
        assert combinators == []

    def test_descendant(self) -> None:
        parts, combinators = _split_selector_parts(".a .b")
        assert parts == [".a", ".b"]
        assert combinators == [" "]

    def test_child(self) -> None:
        parts, combinators = _split_selector_parts(".a > .b")
        assert parts == [".a", ".b"]
        assert combinators == [" > "]

    def test_adjacent(self) -> None:
        parts, combinators = _split_selector_parts(".a + .b")
        assert parts == [".a", ".b"]
        assert combinators == [" + "]

    def test_sibling_no_spaces(self) -> None:
        parts, combinators = _split_selector_parts("a~b")
        assert parts == ["a", "b"]
        assert combinators == ["~"]

    def test_sibling_with_spaces(self) -> None:
        parts, combinators = _split_selector_parts("a ~ b")
        assert parts == ["a", "b"]
        assert combinators == [" ~ "]

    def test_comma_list(self) -> None:
        parts, combinators = _split_selector_parts(".a, .b")
        assert parts == [".a", ".b"]
        assert combinators == [", "]

    def test_nth_child_plus_sign_inside_parens(self) -> None:
        parts, combinators = _split_selector_parts(".x:nth-child(2n+1)")
        assert parts == [".x:nth-child(2n+1)"]
        assert combinators == []

    def test_attribute_value_with_greater_than(self) -> None:
        parts, combinators = _split_selector_parts('[data-x="a>b"]')
        assert parts == ['[data-x="a>b"]']
        assert combinators == []

    def test_attribute_value_with_comma(self) -> None:
        parts, combinators = _split_selector_parts('[title="Hello, World"]')
        assert parts == ['[title="Hello, World"]']
        assert combinators == []

    def test_attribute_value_with_plus(self) -> None:
        parts, combinators = _split_selector_parts('[data-x="a+b"]')
        assert parts == ['[data-x="a+b"]']
        assert combinators == []

    def test_brackets_balanced(self) -> None:
        parts, combinators = _split_selector_parts("[a][b]")
        assert parts == ["[a][b]"]
        assert combinators == []

    def test_newline_descendant(self) -> None:
        parts, combinators = _split_selector_parts(".a\n.b")
        assert parts == [".a", ".b"]
        assert combinators == ["\n"]

    def test_tab_descendant(self) -> None:
        parts, combinators = _split_selector_parts(".a\t.b")
        assert parts == [".a", ".b"]
        assert combinators == ["\t"]

    def test_attribute_selector_attribute_match(self) -> None:
        parts, combinators = _split_selector_parts('[href*="foo"]')
        assert parts == ['[href*="foo"]']
        assert combinators == []

    def test_leading_combinator(self) -> None:
        parts, combinators = _split_selector_parts("> .child")
        assert parts == ["", ".child"]
        assert combinators == ["> "]

    def test_has_function_with_combinator(self) -> None:
        parts, combinators = _split_selector_parts(":has(> img)")
        assert parts == [":has(> img)"]
        assert combinators == []

    def test_escaped_class_name(self) -> None:
        parts, combinators = _split_selector_parts(".\\31 23")
        assert parts == [".\\31 23"]
        assert combinators == []

    def test_escaped_combinator(self) -> None:
        parts, combinators = _split_selector_parts(".a\\, .b")
        assert parts == [".a\\,", ".b"]
        assert combinators == [" "]

    def test_multiple_combinators(self) -> None:
        parts, combinators = _split_selector_parts(".a > .b + .c")
        assert parts == [".a", ".b", ".c"]
        assert combinators == [" > ", " + "]

    def test_string_with_braces(self) -> None:
        parts, combinators = _split_selector_parts('[data-x="a{b"]')
        assert parts == ['[data-x="a{b"]']
        assert combinators == []

    def test_string_with_double_quote_via_single(self) -> None:
        parts, combinators = _split_selector_parts("[data-x='a\"b']")
        assert parts == ["[data-x='a\"b']"]
        assert combinators == []

    def test_attribute_op_tilde_equals(self) -> None:
        parts, combinators = _split_selector_parts('[class~="foo"]')
        assert parts == ['[class~="foo"]']
        assert combinators == []


class TestInsertCid:
    def test_simple_class(self) -> None:
        assert _insert_cid(".x", "1") == ".x[webcompy-cid-1]"

    def test_pseudo_element(self) -> None:
        assert _insert_cid(".x::before", "1") == ".x[webcompy-cid-1]::before"

    def test_pseudo_class_then_pseudo_element(self) -> None:
        assert _insert_cid(".x:hover::before", "1") == ".x:hover[webcompy-cid-1]::before"

    def test_pseudo_element_function(self) -> None:
        assert _insert_cid(".x::slotted(.y)", "1") == ".x[webcompy-cid-1]::slotted(.y)"

    def test_nth_child_preserved(self) -> None:
        assert _insert_cid(".x:nth-child(2n+1)", "1") == ".x:nth-child(2n+1)[webcompy-cid-1]"

    def test_attribute_with_pseudo_element(self) -> None:
        assert _insert_cid('[data-x="a"]::before', "1") == '[data-x="a"][webcompy-cid-1]::before'

    def test_no_pseudo_element_appends_at_end(self) -> None:
        assert _insert_cid(".x", "1") == ".x[webcompy-cid-1]"

    def test_ampersand_inside_parens_ignored(self) -> None:
        assert _insert_cid(".x:has(&)", "1") == ".x:has(&)[webcompy-cid-1]"


class TestScopeSelector:
    def test_simple(self) -> None:
        assert _scope_selector(".x", "1") == ".x[webcompy-cid-1]"

    def test_descendant(self) -> None:
        assert _scope_selector(".a .b", "1") == ".a[webcompy-cid-1] .b[webcompy-cid-1]"

    def test_child(self) -> None:
        assert _scope_selector(".a > .b", "1") == ".a[webcompy-cid-1] > .b[webcompy-cid-1]"

    def test_sibling_no_space(self) -> None:
        assert _scope_selector("a~b", "1") == "a[webcompy-cid-1]~b[webcompy-cid-1]"

    def test_adjacent(self) -> None:
        assert _scope_selector(".a + .b", "1") == ".a[webcompy-cid-1] + .b[webcompy-cid-1]"

    def test_pseudo_element(self) -> None:
        assert _scope_selector(".x::before", "1") == ".x[webcompy-cid-1]::before"

    def test_pseudo_class_then_pseudo_element(self) -> None:
        assert _scope_selector(".x:hover::before", "1") == ".x:hover[webcompy-cid-1]::before"

    def test_nth_child(self) -> None:
        assert _scope_selector(".x:nth-child(2n+1)", "1") == ".x:nth-child(2n+1)[webcompy-cid-1]"

    def test_attribute_value_with_greater_than(self) -> None:
        assert _scope_selector('[data-x="a>b"]', "1") == '[data-x="a>b"][webcompy-cid-1]'

    def test_attribute_value_with_comma(self) -> None:
        assert _scope_selector('[title="Hello, World"]', "1") == '[title="Hello, World"][webcompy-cid-1]'

    def test_newline_descendant(self) -> None:
        assert _scope_selector(".a\n.b", "1") == ".a[webcompy-cid-1]\n.b[webcompy-cid-1]"

    def test_leading_combinator(self) -> None:
        assert _scope_selector("> .child", "1") == "*[webcompy-cid-1]> .child[webcompy-cid-1]"

    def test_has_function_inside(self) -> None:
        assert _scope_selector(":has(> img)", "1") == ":has(> img)[webcompy-cid-1]"

    def test_escaped_class_name(self) -> None:
        assert _scope_selector(".\\31 23", "1") == ".\\31 23[webcompy-cid-1]"

    def test_comma_list(self) -> None:
        assert _scope_selector(".a, .b", "1") == ".a[webcompy-cid-1], .b[webcompy-cid-1]"

    def test_ampersand_raises(self) -> None:
        with pytest.raises(WebComPyException) as exc_info:
            _scope_selector(".btn &", "1")
        assert "&" in str(exc_info.value)
        assert "CSS nesting" in str(exc_info.value)

    def test_ampersand_at_start_raises(self) -> None:
        with pytest.raises(WebComPyException):
            _scope_selector("&:hover", "1")

    def test_ampersand_inside_attribute_ignored(self) -> None:
        assert _scope_selector('[href*="&"]', "1") == '[href*="&"][webcompy-cid-1]'

    def test_ampersand_inside_string_ignored(self) -> None:
        assert _scope_selector('[data-x="a&b"]', "1") == '[data-x="a&b"][webcompy-cid-1]'


class TestContainsTopLevelAmpersand:
    def test_no_ampersand(self) -> None:
        assert _contains_top_level_ampersand(".x") is False

    def test_top_level_ampersand(self) -> None:
        assert _contains_top_level_ampersand(".btn &") is True

    def test_inside_parens(self) -> None:
        assert _contains_top_level_ampersand(":has(> &)") is False

    def test_inside_brackets(self) -> None:
        assert _contains_top_level_ampersand('[href*="&"]') is False

    def test_inside_string(self) -> None:
        assert _contains_top_level_ampersand('[data-x="&"]') is False
