from __future__ import annotations

import asyncio
import re

import pytest

from webcompy.components import (
    ComponentContext,
    define_component,
    on_mounted,
    on_unmounted,
    reactive_scoped_style,
)
from webcompy.components._generator import ComponentGenerator
from webcompy.components._libs import WebComPyComponentException
from webcompy.elements import html
from webcompy.exception import WebComPyException
from webcompy_testing import TestRenderer

_CID_RE = re.compile(r"webcompy-cid-\w+")


def _normalise_cids(css: str) -> str:
    return _CID_RE.sub("CID", css)


class TestDefineComponentValidation:
    def test_named_decorator_stores_name(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert MyCard.custom_element_name == "my-card"

    @pytest.mark.parametrize(
        "name",
        [
            "nocard",
            "My-Card",
            "my-card!",
            "my card",
            "",
            "my_card",
            "font-face",
            "annotation-xml",
            "color-profile",
            "missing-glyph",
        ],
    )
    def test_invalid_custom_element_name_rejected(self, name: str) -> None:
        with pytest.raises(WebComPyComponentException):
            define_component(name)

    def test_observed_attributes_normalised_to_lowercase(self) -> None:
        @define_component(observed_attributes=("Theme-Color",))
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert MyCard.observed_attributes == ("theme-color",)
        assert MyCard.observed_prop_keys == {"theme-color": "theme_color"}

    def test_duplicate_observed_attribute_rejected(self) -> None:
        with pytest.raises(WebComPyComponentException, match="Duplicate"):
            define_component("my-card", observed_attributes=("theme", "theme"))

    def test_string_observed_attributes_rejected(self) -> None:
        with pytest.raises(WebComPyComponentException, match="not a single string"):
            define_component("my-card", observed_attributes="theme")

    def test_reserved_framework_attribute_rejected(self) -> None:
        with pytest.raises(WebComPyComponentException, match="Framework attribute"):
            define_component("my-card", observed_attributes=("webcompy-component",))
        with pytest.raises(WebComPyComponentException, match="Framework attribute"):
            define_component("my-card", observed_attributes=("webcompy-cid-abc",))

    def test_prop_key_collision_rejected(self) -> None:
        with pytest.raises(WebComPyComponentException, match="collide"):
            define_component("my-card", observed_attributes=("foo-bar", "foo_bar"))

    def test_definition_key_format(self) -> None:
        @define_component(observed_attributes=("theme-color",))
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert MyCard.definition_key == "webcompy-v1:my-card:theme-color"

    def test_definition_key_order_independent(self) -> None:
        @define_component(observed_attributes=("theme-color", "size"))
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        @define_component(observed_attributes=("size", "theme-color"))
        def OtherCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert MyCard.definition_key == "webcompy-v1:my-card:size,theme-color"
        assert OtherCard.definition_key == "webcompy-v1:other-card:size,theme-color"

    def test_generator_is_callable(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert isinstance(MyCard, ComponentGenerator)


class TestFlexibleNaming:
    @staticmethod
    def _definition_named(name: str):
        def component(context: ComponentContext[None]):
            return html.DIV({}, "card")

        component.__name__ = name
        return component

    def test_derived_name_from_multi_word_function(self) -> None:
        @define_component()
        def UserCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert UserCard.custom_element_name == "user-card"

    def test_non_round_tripping_acronym_accepted(self) -> None:
        @define_component()
        def HTTPRequest(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert HTTPRequest.custom_element_name == "http-request"

    def test_explicit_tag_decoupled_from_function_name(self) -> None:
        @define_component("user-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert Card.custom_element_name == "user-card"

    def test_explicit_tag_by_keyword(self) -> None:
        @define_component(custom_element_name="user-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert Card.custom_element_name == "user-card"

    def test_kwargs_only_form_derives_name_and_normalises_attributes(self) -> None:
        @define_component(observed_attributes=("Theme-Color",))
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert MyCard.custom_element_name == "my-card"
        assert MyCard.observed_attributes == ("theme-color",)

    @pytest.mark.parametrize("function_name", ["App", "FontFace", "my_card", "_Card"])
    def test_derivation_failure_guides_rename_or_explicit_tag(self, function_name: str) -> None:
        with pytest.raises(WebComPyComponentException) as exc_info:
            define_component()(self._definition_named(function_name))

        message = str(exc_info.value)
        assert f"'{function_name}'" in message
        assert "Rename the function" in message
        assert "use @define_component" in message or "@define_component(" in message

    def test_reserved_derived_name_reports_derived_value(self) -> None:
        with pytest.raises(WebComPyComponentException) as exc_info:
            define_component()(self._definition_named("FontFace"))

        assert "font-face" in str(exc_info.value)

    def test_invalid_explicit_tags_still_rejected(self) -> None:
        for name in ["nocard", "My-Card", "", "my_card", "font-face"]:
            with pytest.raises(WebComPyComponentException):
                define_component(name)

    def test_bare_application_rejected_with_guidance(self) -> None:
        def UserCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with pytest.raises(WebComPyComponentException, match="parentheses"):
            define_component(UserCard)

    def test_redecorating_a_generator_rejected(self) -> None:
        @define_component()
        def UserCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with pytest.raises(WebComPyComponentException, match="component definition"):
            define_component("other-card")(UserCard)

    def test_redecorating_a_marked_function_rejected(self) -> None:
        definition = self._definition_named("UserCard")
        define_component("user-card")(definition)

        with pytest.raises(WebComPyComponentException, match="already"):
            define_component("other-card")(definition)


class TestDisplayArgument:
    def test_display_stored_on_generator(self) -> None:
        @define_component(display="block")
        def UserCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert UserCard.display == "block"

    def test_display_defaults_to_none(self) -> None:
        @define_component()
        def UserCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert UserCard.display is None

    def test_display_rule_emitted_first(self) -> None:
        @define_component(display="block")
        def UserCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        UserCard.scoped_style = {":host": {"color": "red"}}
        css = _normalise_cids(UserCard.scoped_style)
        assert css.startswith("@layer webcompy-scope { user-card[CID] { display: block; }")
        assert ":host" not in css
        assert "color: red" in css

    def test_display_rule_emitted_without_scoped_style(self) -> None:
        @define_component(display="block")
        def UserCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        css = _normalise_cids(UserCard.scoped_style)
        assert css == "@layer webcompy-scope { user-card[CID] { display: block; } }"

    def test_author_host_rule_follows_display_rule(self) -> None:
        @define_component(display="block")
        def UserCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        UserCard.scoped_style = {":host": {"display": "flex"}}
        css = _normalise_cids(UserCard.scoped_style)
        display_idx = css.find("display: block")
        host_idx = css.find("display: flex")
        assert display_idx != -1
        assert host_idx != -1
        assert display_idx < host_idx

    @pytest.mark.parametrize("value", ["bolck", "BLOCK", "inline-flexx", "grid ", "table"])
    def test_invalid_display_value_rejected(self, value: str) -> None:
        with pytest.raises(WebComPyComponentException, match="Invalid display"):
            define_component("user-card", display=value)  # type: ignore[arg-type]

    def test_invalid_display_value_lists_values_in_declared_order(self) -> None:
        with pytest.raises(WebComPyComponentException) as exc_info:
            define_component("user-card", display="bolck")  # type: ignore[arg-type]
        expected = "contents, block, inline, inline-block, flex, inline-flex, grid, inline-grid, flow-root"
        assert expected in str(exc_info.value)

    def test_unhashable_display_value_rejected(self) -> None:
        with pytest.raises(WebComPyComponentException, match="Invalid display"):
            define_component("user-card", display=[])  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "value",
        ["contents", "block", "inline", "inline-block", "flex", "inline-flex", "grid", "inline-grid", "flow-root"],
    )
    def test_valid_display_values_accepted(self, value: str) -> None:
        @define_component("user-card", display=value)  # type: ignore[arg-type]
        def UserCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert UserCard.display == value


class TestStoreCustomElementNameUniqueness:
    def _make_generator(self, name: str, custom_element_name: str) -> ComponentGenerator:
        from webcompy.components._generator import ComponentGenerator as _CG

        def _setup(context: ComponentContext[None]):
            return html.DIV({}, "x")

        return _CG(name, _setup, custom_element_name=custom_element_name)

    def test_colliding_custom_element_names_rejected(self) -> None:
        from webcompy.components._generator import ComponentStore

        gen_a = self._make_generator("CardA", "my-card")
        gen_b = self._make_generator("CardB", "my-card")
        store = ComponentStore()
        store.add_component("CardA", gen_a)
        with pytest.raises(WebComPyComponentException, match="Duplicated Custom Element Name"):
            store.add_component("CardB", gen_b)

    def test_distinct_custom_element_names_accepted(self) -> None:
        from webcompy.components._generator import ComponentStore

        store = ComponentStore()
        store.add_component("CardA", self._make_generator("CardA", "my-card"))
        store.add_component("CardB", self._make_generator("CardB", "other-card"))
        assert set(store.components) == {"CardA", "CardB"}

    def test_same_generator_name_duplicate_rejected(self) -> None:
        from webcompy.components._generator import ComponentStore

        store = ComponentStore()
        store.add_component("CardA", self._make_generator("CardA", "my-card"))
        with pytest.raises(WebComPyComponentException, match="Duplicated Component Name"):
            store.add_component("CardA", self._make_generator("CardA", "other-card"))


class TestNamedComponentRendering:
    def test_single_root_renders_inside_wrapper(self) -> None:
        @define_component()
        def E2eCard(context: ComponentContext[None]):
            return html.DIV({"class": "inner"}, "content")

        with TestRenderer.render(E2eCard) as result:
            root = result._root_node
            assert root.nodeName.lower() == "e2e-card"
            assert root.childNodes.length == 1
            assert root.childNodes[0].nodeName.lower() == "div"
            assert result.query_selector("div") is not None

    def test_multi_root_renders_ordered_children(self) -> None:
        @define_component()
        def E2eCard(context: ComponentContext[None]):
            return [html.HEADER({}, "H"), html.MAIN({}, "M"), html.FOOTER({}, "F")]

        with TestRenderer.render(E2eCard) as result:
            root = result._root_node
            assert root.nodeName.lower() == "e2e-card"
            tags = [root.childNodes[i].nodeName.lower() for i in range(root.childNodes.length)]
            assert tags == ["header", "main", "footer"]

    def test_multi_root_tuple_renders(self) -> None:
        @define_component()
        def E2eCard(context: ComponentContext[None]):
            return (html.HEADER({}, "H"), html.MAIN({}, "M"))

        with TestRenderer.render(E2eCard) as result:
            root = result._root_node
            assert root.childNodes.length == 2

    def test_empty_sequence_renders_empty_wrapper(self) -> None:
        @define_component()
        def E2eCard(context: ComponentContext[None]):
            return []

        with TestRenderer.render(E2eCard) as result:
            root = result._root_node
            assert root.nodeName.lower() == "e2e-card"
            assert root.childNodes.length == 0

    def test_text_child_renders_inside_wrapper(self) -> None:
        @define_component()
        def E2eCard(context: ComponentContext[None]):
            return "plain text"

        with TestRenderer.render(E2eCard) as result:
            root = result._root_node
            assert root.nodeName.lower() == "e2e-card"
            assert root.childNodes.length == 1

    def test_wrapper_reports_one_parent_facing_node(self) -> None:
        @define_component()
        def E2eCard(context: ComponentContext[None]):
            return [html.HEADER({}, "H"), html.MAIN({}, "M")]

        with TestRenderer.render(E2eCard) as result:
            assert result._instance._node_count == 1

    def test_template_root_attrs_not_copied_to_wrapper(self) -> None:
        @define_component()
        def E2eCard(context: ComponentContext[None]):
            return html.DIV({"class": "inner", "data-x": "1"}, "content")

        with TestRenderer.render(E2eCard) as result:
            root = result._root_node
            assert root.getAttribute("class") is None
            assert root.getAttribute("data-x") is None
            inner = result.query_selector("div")
            assert inner is not None
            assert inner.getAttribute("class") == "inner"

    def test_wrapper_carries_framework_markers(self) -> None:
        @define_component()
        def E2eCard(context: ComponentContext[None]):
            return html.DIV({}, "content")

        with TestRenderer.render(E2eCard) as result:
            root = result._root_node
            assert root.getAttribute("webcompy-component") == "E2eCard"
            assert any(name.startswith("webcompy-cid-") for name in root.getAttributeNames())

    def test_nested_named_components(self) -> None:
        @define_component()
        def InnerCard(context: ComponentContext[None]):
            return html.P({}, "inner")

        @define_component()
        def OuterCard(context: ComponentContext[None]):
            return html.DIV({}, InnerCard({}))

        with TestRenderer.render(OuterCard) as result:
            assert result.query_selector("outer-card") is not None
            inner = result.query_selector("inner-card")
            assert inner is not None
            assert inner.parentNode is result.query_selector("div")

    def test_keyed_repeat_preserves_wrapper_per_item(self) -> None:
        from webcompy.elements import repeat
        from webcompy.signal import use_reactive_list

        @define_component()
        def ItemCard(context: ComponentContext[None]):
            return [html.SPAN({}, "a"), html.SPAN({}, "b")]

        @define_component()
        def ListPage(context: ComponentContext[None]):
            items = use_reactive_list(lambda: [{"id": "1"}, {"id": "2"}])
            return html.UL(
                {},
                repeat(items, lambda item, k: ItemCard({}), key=lambda item: item["id"]),
            )

        with TestRenderer.render(ListPage) as result:
            cards = result.query_selector_all("item-card")
            assert len(cards) == 2
            for card in cards:
                assert card.childNodes.length == 2


class TestUnnamedComponentRestrictions:
    def test_invalid_named_children_rejected(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return [html.DIV({}, "a"), [html.SPAN({}, "b")]]

        with pytest.raises(WebComPyComponentException, match="nested sequences"):
            TestRenderer.render(MyCard)

        @define_component("my-card-2")
        def MyCard2(context: ComponentContext[None]):
            return 42

        with pytest.raises(WebComPyComponentException, match="nested sequences"):
            TestRenderer.render(MyCard2)

    def test_decorators_outside_setup_raise(self) -> None:
        with pytest.raises(LookupError):
            on_mounted(lambda: None)
        with pytest.raises(LookupError):
            on_unmounted(lambda: None)


class TestDocumentConnectionHooks:
    def test_named_component_stores_hooks(self) -> None:
        @define_component()
        def E2eCard(context: ComponentContext[None]):
            @on_mounted
            def mounted() -> None:
                pass

            context.on_unmounted(lambda: None)
            return html.DIV({}, "card")

        with TestRenderer.render(E2eCard) as result:
            assert result._instance._property["on_mounted"] is not None
            assert result._instance._property["on_unmounted"] is not None

    def test_named_component_without_hooks_uses_defaults(self) -> None:
        @define_component()
        def E2eCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(E2eCard) as result:
            assert result._instance._property["on_mounted"] is not None
            assert result._instance._property["on_unmounted"] is not None


class TestObservedAttributeProps:
    def test_observed_key_exists_as_none_during_setup(self) -> None:
        seen: list[object] = []

        @define_component(observed_attributes=("theme-color",))
        def E2eCard(context: ComponentContext[None]):
            seen.append(context.props["theme_color"])
            return html.DIV({}, "card")

        with TestRenderer.render(E2eCard):
            pass
        assert seen == [None]

    def test_caller_mapping_preserved_for_other_keys(self) -> None:
        from webcompy_testing import create_test_app

        @define_component(observed_attributes=("theme-color",))
        def E2eCard(context: ComponentContext[None]):
            return html.SPAN({}, str(context.props["label"]))

        @define_component()
        def TestRoot(context: ComponentContext[None]):
            return html.DIV({}, "root")

        app = create_test_app(root_component=TestRoot)
        ctx = app.create_render_context("/")
        try:
            with ctx.di_scope:
                instance = E2eCard({"label": "hello"})
            assert instance._observed_props is not None
            assert instance._observed_props.value["label"] == "hello"
            assert instance._observed_props.value["theme_color"] is None
        finally:
            ctx.dispose()

    def test_observed_props_are_reactive_dict(self) -> None:
        @define_component(observed_attributes=("theme-color",))
        def E2eCard(context: ComponentContext[None]):
            return html.SPAN({}, str(context.props["theme_color"]))

        with TestRenderer.render(E2eCard) as result:
            assert result._instance._observed_props is not None

    def test_caller_observed_value_preserved_when_attribute_absent(self) -> None:
        @define_component(observed_attributes=("theme-color",))
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            node = result._instance._node_cache
            assert node is not None
            adopted = MyCard({"theme_color": "dark"})
            adopted._adopt_node(node)
            assert adopted._observed_props is not None
            assert adopted._observed_props.value["theme_color"] == "dark"

    def test_dom_attribute_wins_at_bind(self) -> None:
        @define_component(observed_attributes=("theme-color",))
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            node = result._instance._node_cache
            assert node is not None
            node.setAttribute("theme-color", "light")
            adopted = MyCard({"theme_color": "dark"})
            adopted._adopt_node(node)
            assert adopted._observed_props is not None
            assert adopted._observed_props.value["theme_color"] == "light"

    def test_caller_reactive_dict_not_mutated(self) -> None:
        from webcompy.signal import ReactiveDict
        from webcompy_testing import create_test_app

        @define_component(observed_attributes=("theme-color",))
        def E2eCard(context: ComponentContext[None]):
            return html.SPAN({}, str(context.props["label"]))

        @define_component()
        def TestRoot(context: ComponentContext[None]):
            return html.DIV({}, "root")

        caller_props = ReactiveDict({"label": "hello"})
        app = create_test_app(root_component=TestRoot)
        ctx = app.create_render_context("/")
        try:
            with ctx.di_scope:
                instance = E2eCard(caller_props)
            assert instance._observed_props is not None
            assert instance._observed_props is not caller_props
            assert instance._observed_props.value["label"] == "hello"
            assert instance._observed_props.value["theme_color"] is None
            assert caller_props.value == {"label": "hello"}
        finally:
            ctx.dispose()

    def test_non_mapping_props_rejected(self) -> None:
        from webcompy_testing import create_test_app

        @define_component(observed_attributes=("theme-color",))
        def E2eCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        @define_component()
        def TestRoot(context: ComponentContext[None]):
            return html.DIV({}, "root")

        app = create_test_app(root_component=TestRoot)
        ctx = app.create_render_context("/")
        try:
            with ctx.di_scope, pytest.raises(WebComPyComponentException, match="mapping props"):
                E2eCard("not-a-mapping")
        finally:
            ctx.dispose()


class TestCustomElementPorts:
    def test_port_abc_not_instantiable(self) -> None:
        from webcompy.ports import CustomElementPort

        with pytest.raises(TypeError):
            CustomElementPort()  # type: ignore[abstract]

    def test_port_importable_from_ports(self) -> None:
        from webcompy.ports import CUSTOM_ELEMENT_PORT_KEY, CustomElementPort

        assert CustomElementPort is not None
        assert CUSTOM_ELEMENT_PORT_KEY is not None

    def test_server_port_is_noop(self) -> None:
        from webcompy_server.ports._custom_element import ServerCustomElementPort

        port = ServerCustomElementPort()
        port.ensure_defined("my-card", ("theme-color",), "key")
        binding = port.bind(
            None,  # type: ignore[arg-type]
            observed_attributes=(),
            on_connected=lambda: None,
            on_disconnected=lambda: None,
            on_attribute_changed=lambda name, value: None,
        )
        binding.dispose()
        assert port.is_document_connected(None) is False  # type: ignore[arg-type]

    def test_fake_port_records_calls(self) -> None:
        from webcompy_testing import FakeCustomElementPort

        port = FakeCustomElementPort()
        port.ensure_defined("my-card", ("theme-color",), "key")
        binding = port.bind(
            object(),
            observed_attributes=("theme-color",),
            on_connected=lambda: None,
            on_disconnected=lambda: None,
            on_attribute_changed=lambda name, value: None,
        )
        assert port.ensure_defined_calls == [("my-card", ("theme-color",), "key")]
        assert len(port.bind_calls) == 1
        assert port.bind_calls[0][1] == ("theme-color",)
        binding.dispose()
        assert port.disposed_bindings == 1

    def test_browser_port_unavailable_outside_browser(self) -> None:
        from webcompy.exception import WebComPyException
        from webcompy.ports._browser._custom_element import BrowserCustomElementPort

        with pytest.raises(WebComPyException):
            BrowserCustomElementPort()


class TestHostSelectorScoping:
    def test_host_selector(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        MyCard.scoped_style = {":host": {"display": "block"}}
        css = MyCard.scoped_style
        assert "my-card[webcompy-cid-" in css
        assert ":host" not in css

    def test_host_compound_selector(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        MyCard.scoped_style = {":host(.compact)": {"padding": "0"}}
        css = MyCard.scoped_style
        assert "my-card.compact[webcompy-cid-" in css

    def test_host_with_descendant(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        MyCard.scoped_style = {":host .inner": {"color": "red"}}
        css = MyCard.scoped_style
        assert "my-card[webcompy-cid-" in css
        assert ".inner[webcompy-cid-" in css

    def test_host_with_pseudo_and_attribute(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        MyCard.scoped_style = {
            ":host:hover": {"color": "red"},
            ":host[data-x]": {"display": "block"},
        }
        css = MyCard.scoped_style
        assert "my-card" in css
        assert ":hover" in css
        assert "[data-x]" in css
        assert css.count("webcompy-cid-") == 2

    def test_host_inside_media_query(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        MyCard.scoped_style = {"@media (max-width: 768px)": {":host": {"display": "none"}}}
        css = MyCard.scoped_style
        assert "@media (max-width: 768px)" in css
        assert "my-card[webcompy-cid-" in css
        assert ":host" not in css

    @pytest.mark.parametrize(
        "selector",
        [
            ":host-context(.dark)",
            ":host(.a .b)",
            ":host()",
            ":host(article)",
            ":host(*.dark)",
            ":host.foo",
            ":host#id",
            ":not(:host)",
            ":is(.a, :host)",
            ".card:host",
            "div :host",
            ".x :host:hover",
        ],
    )
    def test_unsupported_host_forms_rejected(self, selector: str) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with pytest.raises(WebComPyException, match=":host"):
            MyCard.scoped_style = {selector: {"color": "red"}}

    def test_host_like_pseudo_not_treated_as_host(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        MyCard.scoped_style = {":hostel": {"color": "red"}}
        css = MyCard.scoped_style
        assert ":hostel" in css
        assert "my-card" not in css

    def test_host_forms_rejected_in_nested_and_at_rule(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        MyCard.scoped_style = {".x": {":host-context(.dark)": {"color": "red"}}}
        with pytest.raises(WebComPyException, match=":host"):
            _ = MyCard.scoped_style

        MyCard.scoped_style = {"@media (max-width: 768px)": {":host-context(.dark)": {"color": "red"}}}
        with pytest.raises(WebComPyException, match=":host"):
            _ = MyCard.scoped_style

        MyCard.scoped_style = {".x": {":not(:host)": {"color": "red"}}}
        with pytest.raises(WebComPyException, match=":host"):
            _ = MyCard.scoped_style

        MyCard.scoped_style = {"@media (max-width: 768px)": {":not(:host)": {"color": "red"}}}
        with pytest.raises(WebComPyException, match=":host"):
            _ = MyCard.scoped_style

    def test_nested_host_key_rejected(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        MyCard.scoped_style = {".x": {":host": {"color": "red"}}}
        with pytest.raises(WebComPyException, match=":host"):
            _ = MyCard.scoped_style

    def test_reactive_host_matches_static(self) -> None:
        @define_component()
        def RxCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        RxCard.scoped_style = {
            ":host": {"color": "blue"},
            ":host(.active)": {"font-weight": "bold"},
        }
        static = _normalise_cids(RxCard.scoped_style)

        style = reactive_scoped_style(lambda: {":host": {"color": "blue"}, ":host(.active)": {"font-weight": "bold"}})
        style._bind(RxCard._id, host_tag="rx-card")
        reactive = _normalise_cids(style.render_css(RxCard._id))
        assert reactive == static


class TestSSRSerialization:
    def test_ssr_contains_named_wrapper(self) -> None:
        @define_component()
        def E2eCard(context: ComponentContext[None]):
            return [html.HEADER({}, "H"), html.MAIN({}, "M")]

        with TestRenderer.render(E2eCard) as result:
            html_out = result.to_html()
            assert "<e2e-card" in html_out
            assert "<header" in html_out
            assert "<main" in html_out
            assert "</e2e-card>" in html_out


async def _dummy_async_template():
    return html.DIV({}, "resolved")


class TestComponentBindingLifecycle:
    def test_unmounted_hook_fires_after_node_removed(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            instance = result._instance
            order: list[str] = []
            instance._property["on_unmounted"] = lambda: order.append("unmounted")
            instance._property["on_before_destroy"] = lambda: order.append("before_destroy")
            instance._mount_delivered = True
            node = instance._node_cache
            assert node is not None
            instance._remove_element()
            assert order == ["unmounted", "before_destroy"]
            assert node.parentNode is None
            assert instance._node_cache is None

    def test_pending_async_remove_disposes_binding(self) -> None:
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY

        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            instance = result._instance
            port = result._scope.inject(CUSTOM_ELEMENT_PORT_KEY)
            assert port is not None
            instance._pending_async_template = _dummy_async_template()
            instance._remove_element()
            assert port.disposed_bindings == 1
            assert instance._destroyed is True

    def test_pending_async_detach_disposes_binding(self) -> None:
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY

        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            instance = result._instance
            port = result._scope.inject(CUSTOM_ELEMENT_PORT_KEY)
            assert port is not None
            instance._pending_async_template = _dummy_async_template()
            instance._detach_from_node()
            assert port.disposed_bindings == 1
            assert instance._destroyed is True

    def test_bind_to_connected_node_fires_mount(self) -> None:
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY

        mounted: list[int] = []

        @define_component()
        def MyCard(context: ComponentContext[None]):
            @on_mounted
            def mounted_hook():
                mounted.append(1)

            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            port = result._scope.inject(CUSTOM_ELEMENT_PORT_KEY)
            assert port is not None
            node = result._instance._node_cache
            assert node is not None
            port.connected = True
            adopted = MyCard(None)
            adopted._adopt_node(node)
            assert mounted == [1]

    def test_flush_deferred_while_pending_async(self) -> None:
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY

        @define_component()
        async def MyCard(context: ComponentContext[None]):
            await asyncio.sleep(0)

            @on_mounted
            def mounted_hook() -> None:
                pass

            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            port = result._scope.inject(CUSTOM_ELEMENT_PORT_KEY)
            assert port is not None
            node = result._instance._node_cache
            assert node is not None
            port.connected = True
            pending = MyCard(None)
            assert pending._pending_async_template is not None
            pending._adopt_node(node)
            pending._flush_connection_state()
            assert pending._mount_delivered is False

    @pytest.mark.asyncio
    async def test_async_named_component_hydration_round_trip(self) -> None:
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY
        from webcompy_testing._dom import FakeDOMNode

        mounted: list[str] = []

        @define_component()
        async def MyCard(context: ComponentContext[None]):
            await asyncio.sleep(0)

            @on_mounted
            def mounted_hook() -> None:
                mounted.append("mounted")

            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            port = result._scope.inject(CUSTOM_ELEMENT_PORT_KEY)
            assert port is not None
            pending = MyCard(None)
            assert pending._pending_async_template is not None
            parent_node = result._instance._parent._node
            prerendered = FakeDOMNode("my-card")
            prerendered.__webcompy_prerendered_node__ = True
            parent_node.appendChild(prerendered)
            pending._node_idx = 1
            pending._parent = result._instance._parent
            port.connected = True
            assert pending._hydrate_node() is None
            assert pending._node_cache is None
            await pending._render()
            assert pending._node_cache is prerendered
            assert mounted == ["mounted"]

    @pytest.mark.asyncio
    async def test_hydrated_async_named_component_fires_mount_after_await(self) -> None:
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY

        mounted: list[str] = []

        @define_component()
        async def MyCard(context: ComponentContext[None]):
            await asyncio.sleep(0)

            @on_mounted
            def mounted_hook() -> None:
                mounted.append("mounted")

            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            port = result._scope.inject(CUSTOM_ELEMENT_PORT_KEY)
            assert port is not None
            node = result._instance._node_cache
            assert node is not None
            port.connected = True
            adopted = MyCard(None)
            adopted._adopt_node(node)
            await adopted._render()
            assert mounted == ["mounted"]

    def test_adopt_preserves_wrapper_class(self) -> None:
        @define_component(observed_attributes=("theme-color",))
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            node = result._instance._node_cache
            assert node is not None
            node.setAttribute("class", "compact")
            adopted = MyCard(None)
            adopted._adopt_node(node)
            assert node.getAttribute("class") == "compact"

    def test_adopt_preserves_non_framework_attributes(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            node = result._instance._node_cache
            assert node is not None
            node.setAttribute("aria-label", "card")
            node.setAttribute("data-role", "summary")
            adopted = MyCard(None)
            adopted._adopt_node(node)
            assert node.getAttribute("aria-label") == "card"
            assert node.getAttribute("data-role") == "summary"

    def test_adopt_strips_stale_framework_markers(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            node = result._instance._node_cache
            assert node is not None
            node.setAttribute("webcompy-cid-stale", "true")
            node.setAttribute("aria-label", "card")
            adopted = MyCard(None)
            adopted._adopt_node(node)
            assert node.getAttribute("webcompy-cid-stale") is None
            assert node.getAttribute("aria-label") == "card"

    def test_unmounted_suppressed_while_node_connected(self) -> None:
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY

        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            instance = result._instance
            port = result._scope.inject(CUSTOM_ELEMENT_PORT_KEY)
            assert port is not None
            fired: list[str] = []
            instance._property["on_unmounted"] = lambda: fired.append("unmounted")
            instance._mount_delivered = True
            port.connected = True
            instance._remove_element(remove_node=False)
            assert fired == []

    def test_detached_instance_remove_fires_no_unmount(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            instance = result._instance
            fired: list[str] = []
            instance._property["on_unmounted"] = lambda: fired.append("unmounted")
            instance._mount_delivered = True
            instance._detach_from_node()
            instance._remove_element()
            assert fired == []

    def test_detach_fires_unmount_when_node_disconnected(self) -> None:
        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(MyCard) as result:
            instance = result._instance
            fired: list[str] = []
            instance._property["on_unmounted"] = lambda: fired.append("unmounted")
            instance._mount_delivered = True
            node = instance._node_cache
            assert node is not None
            node.remove()
            instance._detach_from_node()
            assert fired == ["unmounted"]

    def test_removing_container_subtree_fires_unmount(self) -> None:
        captured: list[object] = []

        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        @define_component()
        def TestRoot(context: ComponentContext[None]):
            card = MyCard(None)
            captured.append(card)
            return html.DIV({}, card)

        with TestRenderer.render(TestRoot) as result:
            card = captured[0]
            fired: list[str] = []
            card._property["on_unmounted"] = lambda: fired.append("unmounted")
            card._mount_delivered = True
            result._instance._remove_element()
            assert fired == ["unmounted"]

    def test_named_component_requires_port(self) -> None:
        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di import DIScope
        from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY

        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with DIScope() as scope:
            scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
            scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())
            instance = MyCard(None)
            with pytest.raises(WebComPyComponentException, match="port"):
                instance._create_node()

    def test_named_component_requires_host_port(self) -> None:
        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore
        from webcompy.di import DIScope
        from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY
        from webcompy_testing import FakeCustomElementPort
        from webcompy_testing._dom import FakeDOMNode

        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with DIScope() as scope:
            scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
            scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())
            scope.provide(CUSTOM_ELEMENT_PORT_KEY, FakeCustomElementPort())
            instance = MyCard(None)
            with pytest.raises(WebComPyComponentException, match="Host port"):
                instance._bind_custom_element(FakeDOMNode("my-card"))

    def test_ensure_defined_conflict_propagates(self) -> None:
        from webcompy.app._root_component import AppDocumentRoot
        from webcompy.components._generator import ComponentStore
        from webcompy.di import DIScope
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY
        from webcompy_testing import FakeCustomElementPort

        @define_component()
        def MyCard(context: ComponentContext[None]):
            return html.DIV({}, "card")

        class _ConflictPort(FakeCustomElementPort):
            def ensure_defined(self, name, observed_attributes, definition_key):
                raise WebComPyComponentException(
                    f"Custom element '{name}' is already defined with incompatible metadata"
                )

        store = ComponentStore()
        store.add_component("MyCard", MyCard)
        root = object.__new__(AppDocumentRoot)
        with DIScope() as scope:
            scope.provide(_COMPONENT_STORE_KEY, store)
            scope.provide(CUSTOM_ELEMENT_PORT_KEY, _ConflictPort())
            with pytest.raises(WebComPyComponentException, match="incompatible"):
                root._ensure_custom_elements_defined()

    def test_async_named_component_renders_multi_root_wrapper(self) -> None:
        @define_component()
        async def MyCard(context: ComponentContext[None]):
            await asyncio.sleep(0)
            return [html.HEADER({}, "H"), html.MAIN({}, "M")]

        with TestRenderer.render(MyCard) as result:
            assert result._instance._node_count == 1
            html_out = result.to_html()
            assert "<my-card" in html_out
            assert "<header" in html_out
            assert "<main" in html_out
