from webcompy.components._libs import (
    ComponentProperty,
    Context,
    generate_id,
)


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
