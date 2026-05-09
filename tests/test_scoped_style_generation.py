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
