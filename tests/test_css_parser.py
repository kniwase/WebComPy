from __future__ import annotations

from webcompy.template import css_text


class TestBasicSelectors:
    def test_class_selector(self):
        assert css_text(".btn { color: red; }") == {".btn": {"color": "red"}}

    def test_id_selector(self):
        assert css_text("#app { color: red; }") == {"#app": {"color": "red"}}

    def test_element_selector(self):
        assert css_text("div { color: red; }") == {"div": {"color": "red"}}

    def test_universal_selector(self):
        assert css_text("* { box-sizing: border-box; }") == {"*": {"box-sizing": "border-box"}}

    def test_empty_body(self):
        assert css_text(".btn {}") == {".btn": {}}

    def test_multiple_top_level_rules(self):
        assert css_text(".a { color: red; } .b { color: blue; }") == {".a": {"color": "red"}, ".b": {"color": "blue"}}

    def test_selector_with_attribute_brackets(self):
        assert css_text("input[type='text'] { color: red; }") == {"input[type='text']": {"color": "red"}}


class TestCombinatorSelectors:
    def test_descendant_combinator(self):
        assert css_text(".a .b { color: red; }") == {".a .b": {"color": "red"}}

    def test_child_combinator(self):
        assert css_text(".a > .b { color: red; }") == {".a > .b": {"color": "red"}}

    def test_adjacent_sibling_combinator(self):
        assert css_text(".a + .b { color: red; }") == {".a + .b": {"color": "red"}}

    def test_general_sibling_combinator(self):
        assert css_text(".a ~ .b { color: red; }") == {".a ~ .b": {"color": "red"}}

    def test_multi_step_combinator_chain(self):
        assert css_text(".a > .b ~ .c { color: red; }") == {".a > .b ~ .c": {"color": "red"}}

    def test_combinator_with_pseudo(self):
        assert css_text(".a:hover > .b { color: red; }") == {".a:hover > .b": {"color": "red"}}


class TestPseudoClasses:
    def test_simple_pseudo(self):
        assert css_text(".x:hover { color: red; }") == {".x:hover": {"color": "red"}}

    def test_focus_pseudo(self):
        assert css_text(".x:focus { color: red; }") == {".x:focus": {"color": "red"}}

    def test_active_pseudo(self):
        assert css_text(".x:active { color: red; }") == {".x:active": {"color": "red"}}

    def test_nth_child_functional_pseudo(self):
        assert css_text(".x:nth-child(2) { color: red; }") == {".x:nth-child(2)": {"color": "red"}}

    def test_nth_child_with_keyword(self):
        assert css_text(".x:nth-child(odd) { color: red; }") == {".x:nth-child(odd)": {"color": "red"}}

    def test_nth_of_type_functional_pseudo(self):
        assert css_text(".x:nth-of-type(2n+1) { color: red; }") == {".x:nth-of-type(2n+1)": {"color": "red"}}

    def test_not_with_simple_selector(self):
        assert css_text(".x:not(.y) { color: red; }") == {".x:not(.y)": {"color": "red"}}

    def test_not_with_nested_parens_colon(self):
        assert css_text(".x:not(.y:disabled) { color: red; }") == {".x:not(.y:disabled)": {"color": "red"}}

    def test_not_with_deeply_nested_parens(self):
        assert css_text(".x:not(.y:not(.z:hover)) { color: red; }") == {".x:not(.y:not(.z:hover))": {"color": "red"}}

    def test_lang_pseudo(self):
        assert css_text(".x:lang(en) { color: red; }") == {".x:lang(en)": {"color": "red"}}

    def test_pseudo_at_top_level(self):
        assert css_text(":root { color: red; }") == {":root": {"color": "red"}}


class TestPseudoElements:
    def test_double_colon_before(self):
        assert css_text(".x::before { content: 'a'; }") == {".x::before": {"content": "'a'"}}

    def test_double_colon_after(self):
        assert css_text(".x::after { content: 'b'; }") == {".x::after": {"content": "'b'"}}

    def test_placeholder_pseudo_element(self):
        assert css_text(".x::placeholder { color: gray; }") == {".x::placeholder": {"color": "gray"}}

    def test_selection_pseudo_element(self):
        assert css_text(".x::selection { color: red; }") == {".x::selection": {"color": "red"}}

    def test_pseudo_element_with_value_preserved(self):
        assert css_text(".x::before { content: 'hello'; display: block; }") == {
            ".x::before": {"content": "'hello'", "display": "block"}
        }


class TestAtRules:
    def test_media_at_rule(self):
        assert css_text("@media (max-width: 768px) { .btn { font-size: 12px; } }") == {
            "@media (max-width: 768px)": {".btn": {"font-size": "12px"}}
        }

    def test_media_with_and_clause(self):
        assert css_text("@media (min-width: 600px) and (max-width: 1200px) { .x { color: red; } }") == {
            "@media (min-width: 600px) and (max-width: 1200px)": {".x": {"color": "red"}}
        }

    def test_supports_at_rule(self):
        assert css_text("@supports (display: grid) { .btn { display: grid; } }") == {
            "@supports (display: grid)": {".btn": {"display": "grid"}}
        }

    def test_container_at_rule(self):
        assert css_text("@container (min-width: 400px) { .card { display: grid; } }") == {
            "@container (min-width: 400px)": {".card": {"display": "grid"}}
        }

    def test_at_rule_paren_colon_not_split(self):
        assert css_text("@media (max-width: 768px) { .btn { color: red; } }")["@media (max-width: 768px)"][".btn"] == {
            "color": "red"
        }


class TestKeyframes:
    def test_keyframes_percentage_selectors(self):
        assert css_text("@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }") == {
            "@keyframes spin": {
                "0%": {"transform": "rotate(0deg)"},
                "100%": {"transform": "rotate(360deg)"},
            }
        }

    def test_keyframes_from_to_keywords(self):
        assert css_text("@keyframes fade { from { opacity: 0; } to { opacity: 1; } }") == {
            "@keyframes fade": {
                "from": {"opacity": "0"},
                "to": {"opacity": "1"},
            }
        }

    def test_keyframes_mixed_percentages_and_keywords(self):
        assert css_text("@keyframes mix { from { opacity: 0; } 50% { opacity: 0.5; } to { opacity: 1; } }") == {
            "@keyframes mix": {
                "from": {"opacity": "0"},
                "50%": {"opacity": "0.5"},
                "to": {"opacity": "1"},
            }
        }

    def test_keyframes_with_multiple_properties_in_step(self):
        assert css_text("@keyframes slide { from { left: 0; opacity: 0; } to { left: 100px; opacity: 1; } }") == {
            "@keyframes slide": {
                "from": {"left": "0", "opacity": "0"},
                "to": {"left": "100px", "opacity": "1"},
            }
        }


class TestNestedAtRules:
    def test_at_rule_inside_at_rule(self):
        assert css_text("@media (max-width: 768px) { @supports (display: grid) { .btn { display: grid; } } }") == {
            "@media (max-width: 768px)": {"@supports (display: grid)": {".btn": {"display": "grid"}}}
        }

    def test_double_nested_at_rules(self):
        assert css_text(
            "@media (max-width: 768px) { "
            "@supports (display: grid) { "
            "@container (min-width: 400px) { .card { display: grid; } } } }"
        ) == {
            "@media (max-width: 768px)": {
                "@supports (display: grid)": {"@container (min-width: 400px)": {".card": {"display": "grid"}}}
            }
        }


class TestMixedDeclarationsAndRules:
    def test_declaration_then_nested_rule(self):
        assert css_text(".btn { color: red; :hover { background: blue; } }") == {
            ".btn": {
                "color": "red",
                ":hover": {"background": "blue"},
            }
        }

    def test_nested_rule_then_declaration(self):
        assert css_text(".btn { :hover { background: blue; } font-size: 14px; }") == {
            ".btn": {
                ":hover": {"background": "blue"},
                "font-size": "14px",
            }
        }

    def test_interleaved_declarations_and_nested_rules(self):
        assert css_text(".btn { color: red; :hover { color: green; } font-size: 14px; :focus { outline: none; } }") == {
            ".btn": {
                "color": "red",
                ":hover": {"color": "green"},
                "font-size": "14px",
                ":focus": {"outline": "none"},
            }
        }

    def test_declaration_after_nested_block(self):
        assert css_text(".btn { :hover { background: blue; } color: red; }") == {
            ".btn": {
                ":hover": {"background": "blue"},
                "color": "red",
            }
        }


class TestComments:
    def test_comment_before_rule(self):
        assert css_text("/* comment */ .btn { color: red; }") == {".btn": {"color": "red"}}

    def test_multiline_block_comment(self):
        assert css_text("/* line one\nline two\nline three */ .btn { color: red; }") == {".btn": {"color": "red"}}

    def test_inline_comment_between_selector_and_brace(self):
        assert css_text(".btn /* inline */ { color: red; }") == {".btn": {"color": "red"}}

    def test_inline_comment_inside_block(self):
        assert css_text(".btn { color: red; /* note */ font-size: 14px; }") == {
            ".btn": {"color": "red", "font-size": "14px"}
        }

    def test_comment_in_property_position_dropped(self):
        assert css_text(".btn { /* skip me */ }") == {".btn": {}}

    def test_comment_only_input(self):
        assert css_text("/* only a comment */") == {}


class TestMultiValueProperties:
    def test_font_family_three_values(self):
        assert css_text(".x { font-family: a, b, c; }") == {".x": {"font-family": "a, b, c"}}

    def test_transform_function_chain(self):
        assert css_text(".x { transform: rotate(45deg) scale(1.5); }") == {
            ".x": {"transform": "rotate(45deg) scale(1.5)"}
        }

    def test_linear_gradient_with_commas_in_parens(self):
        assert css_text(".x { background: linear-gradient(red, blue); }") == {
            ".x": {"background": "linear-gradient(red, blue)"}
        }

    def test_complex_value_with_nested_parens(self):
        assert css_text(".x { background: calc((100% - 20px) / 2); }") == {
            ".x": {"background": "calc((100% - 20px) / 2)"}
        }

    def test_url_function_value(self):
        assert css_text(".x { background-image: url('/img.png'); }") == {".x": {"background-image": "url('/img.png')"}}

    def test_trailing_semicolon_stripped(self):
        assert css_text(".x { color: red; }") == {".x": {"color": "red"}}

    def test_no_trailing_semicolon(self):
        assert css_text(".x { color: red }") == {".x": {"color": "red"}}


class TestCSSVariables:
    def test_custom_property_simple(self):
        assert css_text(".x { --custom: value; }") == {".x": {"--custom": "value"}}

    def test_custom_property_color_value(self):
        assert css_text(".x { --my-color: #fff; }") == {".x": {"--my-color": "#fff"}}

    def test_custom_property_with_dashes(self):
        assert css_text(".x { --my-long-prop: 10px; }") == {".x": {"--my-long-prop": "10px"}}

    def test_custom_property_used_along_regular_properties(self):
        assert css_text(".x { color: red; --accent: blue; background: white; }") == {
            ".x": {
                "color": "red",
                "--accent": "blue",
                "background": "white",
            }
        }

    def test_custom_property_with_complex_value(self):
        assert css_text(".x { --shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }") == {
            ".x": {"--shadow": "0 4px 6px rgba(0, 0, 0, 0.1)"}
        }


class TestParenthesisAwareColons:
    def test_inner_colon_in_at_rule_does_not_split_key(self):
        result = css_text("@media (max-width: 768px) { .btn { color: red; } }")
        assert "@media (max-width: 768px)" in result
        assert ":768px" not in result.get("@media (max-width: 768px)", {})

    def test_inner_colon_in_functional_pseudo_preserved(self):
        result = css_text(".x:not(.y:disabled) { color: red; }")
        assert ".x:not(.y:disabled)" in result

    def test_inner_colon_with_multiple_nested_parens(self):
        result = css_text(".x:not(.y:not(.z:checked:hover)) { color: red; }")
        assert ".x:not(.y:not(.z:checked:hover))" in result


class TestMiscEdgeCases:
    def test_empty_input(self):
        assert css_text("") == {}

    def test_whitespace_only_input(self):
        assert css_text("   \n\t  ") == {}

    def test_dedent_applied_before_parsing(self):
        indented = """
            .btn {
                color: red;
            }
        """
        assert css_text(indented) == {".btn": {"color": "red"}}

    def test_multiline_body_preserved(self):
        assert css_text(".btn {\n  color: red;\n  font-size: 14px;\n}") == {
            ".btn": {"color": "red", "font-size": "14px"}
        }

    def test_property_with_special_chars_preserved(self):
        assert css_text(".x { content: 'a > b < c & d'; }") == {".x": {"content": "'a > b < c & d'"}}

    def test_property_with_unicode_value(self):
        assert css_text(".x { content: 'こんにちは'; }") == {".x": {"content": "'こんにちは'"}}

    def test_selector_with_leading_combinator_preserved(self):
        assert css_text("@media (max-width: 768px) { > li { color: blue; } }") == {
            "@media (max-width: 768px)": {"> li": {"color": "blue"}}
        }

    def test_double_colon_pseudo_at_top_level(self):
        assert css_text("::before { color: red; }") == {"::before": {"color": "red"}}
