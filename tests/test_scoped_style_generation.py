import pytest

from webcompy.components._generator import (
    ComponentGenerator,
    _classify_nested_key,
    _generate_css_recursive,
    _process_style_declaration,
)


class TestClassifyNestedKey:
    def test_at_rule_media(self):
        assert _classify_nested_key("@media (max-width: 768px)") == "at-rule"

    def test_at_rule_supports(self):
        assert _classify_nested_key("@supports (display: grid)") == "at-rule"

    def test_at_rule_container(self):
        assert _classify_nested_key("@container (min-width: 400px)") == "at-rule"

    def test_pseudo_class_hover(self):
        assert _classify_nested_key(":hover") == "pseudo"

    def test_pseudo_class_focus(self):
        assert _classify_nested_key(":focus") == "pseudo"

    def test_pseudo_element_before(self):
        assert _classify_nested_key("::before") == "pseudo"

    def test_pseudo_element_after(self):
        assert _classify_nested_key("::after") == "pseudo"

    def test_combinator_child(self):
        assert _classify_nested_key("> li") == "combinator"

    def test_combinator_adjacent(self):
        assert _classify_nested_key("+ p") == "combinator"

    def test_combinator_sibling(self):
        assert _classify_nested_key("~ span") == "combinator"

    def test_combinator_descendant(self):
        assert _classify_nested_key(" .child") == "combinator"


class TestGenerateCssRecursive:
    def test_flat_style(self):
        result = _generate_css_recursive(".btn[webcompy-cid-xxx]", {"color": "blue"})
        assert result == ".btn[webcompy-cid-xxx] { color: blue; }"

    def test_media_at_rule_wrapping(self):
        style_dict = {
            "color": "blue",
            "@media (max-width: 768px)": {"color": "red"},
        }
        result = _generate_css_recursive(".btn[webcompy-cid-xxx]", style_dict)
        assert ".btn[webcompy-cid-xxx] { color: blue; }" in result
        assert "@media (max-width: 768px) { .btn[webcompy-cid-xxx] { color: red; } }" in result

    def test_supports_at_rule_wrapping(self):
        style_dict = {
            "padding": "20px",
            "@supports (display: grid)": {"display": "grid"},
        }
        result = _generate_css_recursive(".card[webcompy-cid-xxx]", style_dict)
        assert ".card[webcompy-cid-xxx] { padding: 20px; }" in result
        assert "@supports (display: grid) { .card[webcompy-cid-xxx] { display: grid; } }" in result

    def test_hover_pseudo_class_no_space(self):
        style_dict = {
            "color": "blue",
            ":hover": {"background": "yellow"},
        }
        result = _generate_css_recursive(".btn[webcompy-cid-xxx]", style_dict)
        assert ".btn[webcompy-cid-xxx] { color: blue; }" in result
        assert ".btn[webcompy-cid-xxx]:hover { background: yellow; }" in result

    def test_after_pseudo_element_no_space(self):
        style_dict = {
            "position": "relative",
            "::after": {"content": "attr(data-tip)"},
        }
        result = _generate_css_recursive(".tooltip[webcompy-cid-xxx]", style_dict)
        assert ".tooltip[webcompy-cid-xxx] { position: relative; }" in result
        assert ".tooltip[webcompy-cid-xxx]::after { content: attr(data-tip); }" in result

    def test_combinator_child_with_space(self):
        style_dict = {
            "color": "black",
            "> li": {"color": "blue"},
        }
        result = _generate_css_recursive(".menu[webcompy-cid-xxx]", style_dict)
        assert ".menu[webcompy-cid-xxx] { color: black; }" in result
        assert ".menu[webcompy-cid-xxx] > li { color: blue; }" in result

    def test_deep_nesting_at_rule_with_pseudo(self):
        style_dict = {
            "color": "blue",
            "@media (max-width: 768px)": {
                "color": "red",
                ":hover": {"background": "yellow"},
            },
        }
        result = _generate_css_recursive(".btn[webcompy-cid-xxx]", style_dict)
        assert ".btn[webcompy-cid-xxx] { color: blue; }" in result
        assert "@media (max-width: 768px) {" in result
        assert ".btn[webcompy-cid-xxx] { color: red; }" in result
        assert ".btn[webcompy-cid-xxx]:hover { background: yellow; }" in result


class TestProcessStyleDeclaration:
    def test_valid_flat_style(self):
        result = _process_style_declaration({"color": "blue"})
        assert result == {"color": "blue"}

    def test_valid_nested_style(self):
        result = _process_style_declaration(
            {
                "color": "blue",
                ":hover": {"background": "yellow"},
            }
        )
        assert result == {
            "color": "blue",
            ":hover": {"background": "yellow"},
        }

    def test_strips_semicolon(self):
        result = _process_style_declaration({"color": "blue;"})
        assert result == {"color": "blue"}

    def test_invalid_type_raises_error(self):
        with pytest.raises(TypeError) as exc_info:
            _process_style_declaration({"color": 123})  # type: ignore
        assert "Invalid style value type" in str(exc_info.value)
        assert "color" in str(exc_info.value)
        assert "int" in str(exc_info.value)

    def test_invalid_nested_type_raises_error(self):
        with pytest.raises(TypeError) as exc_info:
            _process_style_declaration(
                {
                    "color": "blue",
                    ":hover": {"background": None},  # type: ignore
                }
            )
        assert "Invalid style value type" in str(exc_info.value)
        assert "background" in str(exc_info.value)


class TestComponentGeneratorScopedStyle:
    def test_full_integration_flat_style(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {".btn": {"color": "blue", "font-weight": "bold"}}
        css = gen.scoped_style
        assert ".btn[webcompy-cid-" in css
        assert "{ color: blue; font-weight: bold; }" in css

    def test_full_integration_media_wrapping(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {
            ".btn": {
                "color": "blue",
                "@media (max-width: 768px)": {"color": "red"},
            }
        }
        css = gen.scoped_style
        assert ".btn[webcompy-cid-" in css
        assert "{ color: blue; }" in css
        assert "@media (max-width: 768px) {" in css
        assert "{ color: red; }" in css
        assert ".btn[webcompy-cid-" in css.split("@media")[1]

    def test_full_integration_hover_no_space(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {
            ".btn": {
                "color": "blue",
                ":hover": {"background": "yellow"},
            }
        }
        css = gen.scoped_style
        assert ".btn[webcompy-cid-" in css
        assert "{ color: blue; }" in css
        assert ":hover { background: yellow; }" in css
        assert ".btn[webcompy-cid-]:hover" not in css
        assert ".btn[webcompy-cid-" in css.split(":hover")[0]

    def test_top_level_media_at_rule(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {"@media (max-width: 768px)": {".btn": {"color": "red"}}}
        css = gen.scoped_style
        assert "@media (max-width: 768px) {" in css or "@media(max-width:768px){" in css.replace(" ", "")
        assert "@media[webcompy-cid-" not in css
        assert ".btn[webcompy-cid-" in css
        assert "{ color: red; }" in css

    def test_top_level_supports_at_rule(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {"@supports (display: grid)": {".card": {"display": "grid"}}}
        css = gen.scoped_style
        assert "@supports (display: grid)" in css
        assert "@supports[webcompy-cid-" not in css
        assert ".card[webcompy-cid-" in css
        assert "{ display: grid; }" in css

    def test_top_level_at_rule_with_leading_whitespace(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {" @media (max-width: 768px)": {".btn": {"color": "red"}}}
        css = gen.scoped_style
        assert "@media (max-width: 768px)" in css
        assert "@media[webcompy-cid-" not in css
        assert ".btn[webcompy-cid-" in css

    def test_top_level_at_rule_not_scoped(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {"@media (max-width: 768px)": {"nav button": {"display": "block"}}}
        css = gen.scoped_style
        assert "@media[webcompy-cid-" not in css
        assert "nav[webcompy-cid-" in css
        assert "button[webcompy-cid-" in css

    def test_selectors_inside_at_rule_are_scoped(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {
            "@media (max-width: 768px)": {
                ".btn": {"color": "red"},
                "nav a": {"text-decoration": "none"},
            }
        }
        css = gen.scoped_style
        assert ".btn[webcompy-cid-" in css
        assert "nav[webcompy-cid-" in css
        assert "a[webcompy-cid-" in css

    def test_combinator_selector_no_orphan_cid(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {".menu": {"color": "black", "> li": {"color": "blue"}}}
        css = gen.scoped_style
        assert ".menu[webcompy-cid-" in css
        assert "> li" in css
        assert "webcompy-cid-]> li" not in css

    def test_adjacent_combinator_no_orphan_cid(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {"div": {"color": "black", "+ p": {"color": "red"}}}
        css = gen.scoped_style
        assert "+ p" in css
        assert "webcompy-cid-]+ p" not in css

    def test_sibling_combinator_no_orphan_cid(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {"div": {"color": "black", "~ span": {"color": "red"}}}
        css = gen.scoped_style
        assert "~ span" in css
        assert "webcompy-cid-]~ span" not in css

    def test_nested_at_rules(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {"@media (max-width: 768px)": {"@supports (display: grid)": {".card": {"display": "grid"}}}}
        css = gen.scoped_style
        assert "@supports (display: grid) {" in css
        assert "@supports[webcompy-cid-" not in css
        assert ".card[webcompy-cid-" in css

    def test_keyframes_no_cid_on_inner_keys(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {
            "@keyframes spin": {
                "0%": {"transform": "rotate(0deg)"},
                "100%": {"transform": "rotate(360deg)"},
            }
        }
        css = gen.scoped_style
        assert "0% { transform: rotate(0deg); }" in css or "0%{transform:rotate(0deg);}" in css.replace(" ", "")
        assert "100% { transform: rotate(360deg); }" in css or "100%{transform:rotate(360deg);}" in css.replace(" ", "")
        assert "0%[webcompy-cid-" not in css
        assert "100%[webcompy-cid-" not in css

    def test_pseudo_in_top_level_at_rule_is_scoped(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {"@media (max-width: 768px)": {":hover": {"background": "yellow"}}}
        css = gen.scoped_style
        assert "*[webcompy-cid-" in css
        assert ":hover { background: yellow; }" in css or ":hover{background:yellow;}" in css.replace(" ", "")

    def test_combinator_in_top_level_at_rule_is_scoped(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {"@media (max-width: 768px)": {"> li": {"color": "blue"}}}
        css = gen.scoped_style
        assert "webcompy-cid-]> li" not in css
        assert "webcompy-cid-" in css

    def test_keyframes_inside_media_query(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {
            "@media (max-width: 768px)": {"@keyframes fade": {"from": {"opacity": "0"}, "to": {"opacity": "1"}}}
        }
        css = gen.scoped_style
        assert "@keyframes fade" in css
        assert "from[webcompy-cid-" not in css
        assert "to[webcompy-cid-" not in css

    def test_double_nested_at_rules(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {
            "@media (max-width: 768px)": {
                "@supports (display: grid)": {"@container (min-width: 400px)": {".card": {"display": "grid"}}}
            }
        }
        css = gen.scoped_style
        assert "@container (min-width: 400px) {" in css or "@container(min-width:400px){" in css.replace(" ", "")
        assert ".card[webcompy-cid-" in css

    def test_pseudo_element_in_top_level_at_rule(self):
        gen = ComponentGenerator("TestComponent", lambda ctx: None)
        gen.scoped_style = {"@media (max-width: 768px)": {"::after": {"content": "''"}}}
        css = gen.scoped_style
        assert "*[webcompy-cid-" in css
        assert "::after" in css
