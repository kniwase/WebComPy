from webcompy.components._abstract import ComponentAbstract, _camel_to_kebab_pattern
from webcompy.components._decorators import (
    component_template,
    on_after_rendering,
    on_before_destroy,
    on_before_rendering,
)
from webcompy.components._libs import (
    ComponentProperty,
    Context,
    WebComPyComponentException,
    generate_id,
)


class TestDecorators:
    def test_component_template_sets_property(self):
        @component_template
        def template(self):
            return None

        assert hasattr(template, "__webcompy_component_class_property__")
        assert template.__webcompy_component_class_property__ == "template"

    def test_on_before_rendering_sets_property(self):
        @on_before_rendering
        def before_render(self):
            pass

        assert before_render.__webcompy_component_class_property__ == "on_before_rendering"

    def test_on_after_rendering_sets_property(self):
        @on_after_rendering
        def after_render(self):
            pass

        assert after_render.__webcompy_component_class_property__ == "on_after_rendering"

    def test_on_before_destroy_sets_property(self):
        @on_before_destroy
        def before_destroy(self):
            pass

        assert before_destroy.__webcompy_component_class_property__ == "on_before_destroy"

    def test_decorators_preserve_name(self):
        @component_template
        def my_template(self):
            return None

        assert my_template.__name__ == "my_template"


class TestGenerateId:
    def test_generate_id_returns_string(self):
        result = generate_id("TestComponent")
        assert isinstance(result, str)

    def test_generate_id_deterministic(self):
        a = generate_id("TestComponent")
        b = generate_id("TestComponent")
        assert a == b

    def test_generate_id_different_names(self):
        a = generate_id("ComponentA")
        b = generate_id("ComponentB")
        assert a != b


class TestCamelToKebab:
    def test_simple_camel(self):
        assert _camel_to_kebab_pattern.sub(r"-\1", "MyComponent") == "My-Component"

    def test_already_kebab(self):
        result = _camel_to_kebab_pattern.sub(r"-\1", "my-component")
        assert "my" in result


class TestComponentAbstract:
    def test_cannot_instantiate(self):
        try:
            ComponentAbstract()
            raise AssertionError("Should have raised")
        except (WebComPyComponentException, TypeError):
            pass


class TestContext:
    def test_context_stores_props(self):
        ctx = Context(
            props="hello",
            slots={},
            component_name="test",
            title_getter=lambda: "",
            meta_getter=lambda: {},
            title_setter=lambda x: None,
            meta_setter=lambda k, v: None,
        )
        assert ctx.props == "hello"


class TestComponentProperty:
    def test_component_property_is_typed_dict(self):
        prop: ComponentProperty = {
            "component_id": "abc",
            "component_name": "test",
            "template": None,
            "on_before_rendering": lambda: None,
            "on_after_rendering": lambda: None,
            "on_before_destroy": lambda: None,
        }
        assert prop["component_id"] == "abc"
        assert prop["component_name"] == "test"
