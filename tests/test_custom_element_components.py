from __future__ import annotations

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
    def test_bare_decorator_has_no_custom_element_name(self) -> None:
        @define_component
        def Plain(context: ComponentContext[None]):
            return html.DIV({}, "plain")

        assert Plain.custom_element_name is None

    def test_named_decorator_stores_name(self) -> None:
        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert Card.custom_element_name == "my-card"

    @pytest.mark.parametrize(
        "name",
        ["nocard", "My-Card", "my-card!", "my card", "", "my_card"],
    )
    def test_invalid_custom_element_name_rejected(self, name: str) -> None:
        with pytest.raises(WebComPyComponentException):
            define_component(name)

    def test_observed_attributes_normalised_to_lowercase(self) -> None:
        @define_component("my-card", observed_attributes=("Theme-Color",))
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert Card.observed_attributes == ("theme-color",)
        assert Card.observed_prop_keys == {"theme-color": "theme_color"}

    def test_duplicate_observed_attribute_rejected(self) -> None:
        with pytest.raises(WebComPyComponentException, match="Duplicate"):
            define_component("my-card", observed_attributes=("theme", "theme"))

    def test_reserved_framework_attribute_rejected(self) -> None:
        with pytest.raises(WebComPyComponentException, match="Framework attribute"):
            define_component("my-card", observed_attributes=("webcompy-component",))
        with pytest.raises(WebComPyComponentException, match="Framework attribute"):
            define_component("my-card", observed_attributes=("webcompy-cid-abc",))

    def test_prop_key_collision_rejected(self) -> None:
        with pytest.raises(WebComPyComponentException, match="collide"):
            define_component("my-card", observed_attributes=("foo-bar", "foo_bar"))

    def test_definition_key_format(self) -> None:
        @define_component("my-card", observed_attributes=("theme-color",))
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert Card.definition_key == "webcompy-v1:my-card:theme-color"

        @define_component
        def Plain(context: ComponentContext[None]):
            return html.DIV({}, "plain")

        assert Plain.definition_key is None

    def test_generator_is_callable(self) -> None:
        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        assert isinstance(Card, ComponentGenerator)


class TestNamedComponentRendering:
    def test_single_root_renders_inside_wrapper(self) -> None:
        @define_component("e2e-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({"class": "inner"}, "content")

        with TestRenderer.render(Card) as result:
            root = result._root_node
            assert root.nodeName.lower() == "e2e-card"
            assert root.childNodes.length == 1
            assert root.childNodes[0].nodeName.lower() == "div"
            assert result.query_selector("div") is not None

    def test_multi_root_renders_ordered_children(self) -> None:
        @define_component("e2e-card")
        def Card(context: ComponentContext[None]):
            return [html.HEADER({}, "H"), html.MAIN({}, "M"), html.FOOTER({}, "F")]

        with TestRenderer.render(Card) as result:
            root = result._root_node
            assert root.nodeName.lower() == "e2e-card"
            tags = [root.childNodes[i].nodeName.lower() for i in range(root.childNodes.length)]
            assert tags == ["header", "main", "footer"]

    def test_multi_root_tuple_renders(self) -> None:
        @define_component("e2e-card")
        def Card(context: ComponentContext[None]):
            return (html.HEADER({}, "H"), html.MAIN({}, "M"))

        with TestRenderer.render(Card) as result:
            root = result._root_node
            assert root.childNodes.length == 2

    def test_empty_sequence_renders_empty_wrapper(self) -> None:
        @define_component("e2e-card")
        def Card(context: ComponentContext[None]):
            return []

        with TestRenderer.render(Card) as result:
            root = result._root_node
            assert root.nodeName.lower() == "e2e-card"
            assert root.childNodes.length == 0

    def test_text_child_renders_inside_wrapper(self) -> None:
        @define_component("e2e-card")
        def Card(context: ComponentContext[None]):
            return "plain text"

        with TestRenderer.render(Card) as result:
            root = result._root_node
            assert root.nodeName.lower() == "e2e-card"
            assert root.childNodes.length == 1

    def test_wrapper_reports_one_parent_facing_node(self) -> None:
        @define_component("e2e-card")
        def Card(context: ComponentContext[None]):
            return [html.HEADER({}, "H"), html.MAIN({}, "M")]

        with TestRenderer.render(Card) as result:
            assert result._instance._node_count == 1

    def test_template_root_attrs_not_copied_to_wrapper(self) -> None:
        @define_component("e2e-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({"class": "inner", "data-x": "1"}, "content")

        with TestRenderer.render(Card) as result:
            root = result._root_node
            assert root.getAttribute("class") is None
            assert root.getAttribute("data-x") is None
            inner = result.query_selector("div")
            assert inner is not None
            assert inner.getAttribute("class") == "inner"

    def test_wrapper_carries_framework_markers(self) -> None:
        @define_component("e2e-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "content")

        with TestRenderer.render(Card) as result:
            root = result._root_node
            assert root.getAttribute("webcompy-component") == "Card"
            assert any(name.startswith("webcompy-cid-") for name in root.getAttributeNames())

    def test_nested_named_components(self) -> None:
        @define_component("inner-card")
        def Inner(context: ComponentContext[None]):
            return html.P({}, "inner")

        @define_component("outer-card")
        def Outer(context: ComponentContext[None]):
            return html.DIV({}, Inner({}))

        with TestRenderer.render(Outer) as result:
            assert result.query_selector("outer-card") is not None
            inner = result.query_selector("inner-card")
            assert inner is not None
            assert inner.parentNode is result.query_selector("div")

    def test_keyed_repeat_preserves_wrapper_per_item(self) -> None:
        from webcompy.elements import repeat
        from webcompy.signal import use_reactive_list

        @define_component("item-card")
        def ItemCard(context: ComponentContext[None]):
            return [html.SPAN({}, "a"), html.SPAN({}, "b")]

        @define_component
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
    def test_multi_root_rejected(self) -> None:
        @define_component
        def Bad(context: ComponentContext[None]):
            return [html.DIV({}, "a"), html.DIV({}, "b")]

        with pytest.raises(WebComPyException, match="Root Node"):
            TestRenderer.render(Bad)

    def test_context_on_mounted_rejected(self) -> None:
        @define_component
        def Bad(context: ComponentContext[None]):
            context.on_mounted(lambda: None)
            return html.DIV({}, "a")

        with pytest.raises(WebComPyComponentException, match="named"):
            TestRenderer.render(Bad)

    def test_context_on_unmounted_rejected(self) -> None:
        @define_component
        def Bad(context: ComponentContext[None]):
            context.on_unmounted(lambda: None)
            return html.DIV({}, "a")

        with pytest.raises(WebComPyComponentException, match="named"):
            TestRenderer.render(Bad)

    def test_decorator_on_mounted_rejected(self) -> None:
        @define_component
        def Bad(context: ComponentContext[None]):
            @on_mounted
            def mounted() -> None:
                pass

            return html.DIV({}, "a")

        with pytest.raises(WebComPyComponentException, match="named"):
            TestRenderer.render(Bad)

    def test_decorator_on_unmounted_rejected(self) -> None:
        @define_component
        def Bad(context: ComponentContext[None]):
            @on_unmounted
            def unmounted() -> None:
                pass

            return html.DIV({}, "a")

        with pytest.raises(WebComPyComponentException, match="named"):
            TestRenderer.render(Bad)

    def test_decorators_outside_setup_raise(self) -> None:
        with pytest.raises(LookupError):
            on_mounted(lambda: None)
        with pytest.raises(LookupError):
            on_unmounted(lambda: None)


class TestDocumentConnectionHooks:
    def test_named_component_stores_hooks(self) -> None:
        @define_component("e2e-card")
        def Card(context: ComponentContext[None]):
            @on_mounted
            def mounted() -> None:
                pass

            context.on_unmounted(lambda: None)
            return html.DIV({}, "card")

        with TestRenderer.render(Card) as result:
            assert result._instance._property["on_mounted"] is not None
            assert result._instance._property["on_unmounted"] is not None

    def test_named_component_without_hooks_uses_defaults(self) -> None:
        @define_component("e2e-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(Card) as result:
            assert result._instance._property["on_mounted"] is not None
            assert result._instance._property["on_unmounted"] is not None


class TestObservedAttributeProps:
    def test_observed_key_exists_as_none_during_setup(self) -> None:
        seen: list[object] = []

        @define_component("e2e-card", observed_attributes=("theme-color",))
        def Card(context: ComponentContext[None]):
            seen.append(context.props["theme_color"])
            return html.DIV({}, "card")

        with TestRenderer.render(Card):
            pass
        assert seen == [None]

    def test_caller_mapping_preserved_for_other_keys(self) -> None:
        from webcompy_testing import create_test_app

        @define_component("e2e-card", observed_attributes=("theme-color",))
        def Card(context: ComponentContext[None]):
            return html.SPAN({}, str(context.props["label"]))

        @define_component
        def Root(context: ComponentContext[None]):
            return html.DIV({}, "root")

        app = create_test_app(root_component=Root)
        ctx = app.create_render_context("/")
        try:
            with ctx.di_scope:
                instance = Card({"label": "hello"})
            assert instance._observed_props is not None
            assert instance._observed_props.value["label"] == "hello"
            assert instance._observed_props.value["theme_color"] is None
        finally:
            ctx.dispose()

    def test_observed_props_are_reactive_dict(self) -> None:
        @define_component("e2e-card", observed_attributes=("theme-color",))
        def Card(context: ComponentContext[None]):
            return html.SPAN({}, str(context.props["theme_color"]))

        with TestRenderer.render(Card) as result:
            assert result._instance._observed_props is not None

    def test_non_mapping_props_rejected(self) -> None:
        from webcompy_testing import create_test_app

        @define_component("e2e-card", observed_attributes=("theme-color",))
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        @define_component
        def Root(context: ComponentContext[None]):
            return html.DIV({}, "root")

        app = create_test_app(root_component=Root)
        ctx = app.create_render_context("/")
        try:
            with ctx.di_scope, pytest.raises(WebComPyComponentException, match="mapping props"):
                Card("not-a-mapping")
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
        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        Card.scoped_style = {":host": {"display": "block"}}
        css = Card.scoped_style
        assert "my-card[webcompy-cid-" in css
        assert ":host" not in css

    def test_host_compound_selector(self) -> None:
        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        Card.scoped_style = {":host(.compact)": {"padding": "0"}}
        css = Card.scoped_style
        assert "my-card.compact[webcompy-cid-" in css

    def test_host_with_descendant(self) -> None:
        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        Card.scoped_style = {":host .inner": {"color": "red"}}
        css = Card.scoped_style
        assert "my-card[webcompy-cid-" in css
        assert ".inner[webcompy-cid-" in css

    def test_host_with_pseudo_and_attribute(self) -> None:
        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        Card.scoped_style = {
            ":host:hover": {"color": "red"},
            ":host[data-x]": {"display": "block"},
        }
        css = Card.scoped_style
        assert "my-card" in css
        assert ":hover" in css
        assert "[data-x]" in css
        assert css.count("webcompy-cid-") == 2

    def test_host_inside_media_query(self) -> None:
        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        Card.scoped_style = {"@media (max-width: 768px)": {":host": {"display": "none"}}}
        css = Card.scoped_style
        assert "@media (max-width: 768px)" in css
        assert "my-card[webcompy-cid-" in css
        assert ":host" not in css

    @pytest.mark.parametrize(
        "selector",
        [":host-context(.dark)", ":host(.a .b)", ":host()"],
    )
    def test_unsupported_host_forms_rejected(self, selector: str) -> None:
        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with pytest.raises(WebComPyException, match=":host"):
            Card.scoped_style = {selector: {"color": "red"}}

    def test_host_rejected_for_unnamed_component(self) -> None:
        @define_component
        def Plain(context: ComponentContext[None]):
            return html.DIV({}, "plain")

        with pytest.raises(WebComPyException, match=":host"):
            Plain.scoped_style = {":host": {"display": "block"}}

    def test_reactive_host_matches_static(self) -> None:
        @define_component("rx-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        Card.scoped_style = {
            ":host": {"color": "blue"},
            ":host(.active)": {"font-weight": "bold"},
        }
        static = _normalise_cids(Card.scoped_style)

        style = reactive_scoped_style(lambda: {":host": {"color": "blue"}, ":host(.active)": {"font-weight": "bold"}})
        style._bind(Card._id, host_tag="rx-card")
        reactive = _normalise_cids(style.render_css(Card._id))
        assert reactive == static

    def test_reactive_host_rejected_for_unnamed(self) -> None:
        style = reactive_scoped_style(lambda: {":host": {"color": "blue"}})
        with pytest.raises(WebComPyException, match=":host"):
            style._bind("cid123")


class TestSSRSerialization:
    def test_ssr_contains_named_wrapper(self) -> None:
        @define_component("e2e-card")
        def Card(context: ComponentContext[None]):
            return [html.HEADER({}, "H"), html.MAIN({}, "M")]

        with TestRenderer.render(Card) as result:
            html_out = result.to_html()
            assert "<e2e-card" in html_out
            assert "<header" in html_out
            assert "<main" in html_out
            assert "</e2e-card>" in html_out


class TestComponentBindingLifecycle:
    def test_unmounted_hook_fires_after_node_removed(self) -> None:
        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(Card) as result:
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

    def test_bind_to_connected_node_fires_mount(self) -> None:
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY

        mounted: list[int] = []

        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            @on_mounted
            def mounted_hook():
                mounted.append(1)

            return html.DIV({}, "card")

        with TestRenderer.render(Card) as result:
            port = result._scope.inject(CUSTOM_ELEMENT_PORT_KEY)
            assert port is not None
            node = result._instance._node_cache
            assert node is not None
            port.connected = True
            adopted = Card(None)
            adopted._adopt_node(node)
            assert mounted == [1]
    def test_adopt_preserves_wrapper_class(self) -> None:
        @define_component("my-card", observed_attributes=("theme-color",))
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(Card) as result:
            node = result._instance._node_cache
            assert node is not None
            node.setAttribute("class", "compact")
            adopted = Card(None)
            adopted._adopt_node(node)
            assert node.getAttribute("class") == "compact"

    def test_adopt_preserves_non_framework_attributes(self) -> None:
        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(Card) as result:
            node = result._instance._node_cache
            assert node is not None
            node.setAttribute("aria-label", "card")
            node.setAttribute("data-role", "summary")
            adopted = Card(None)
            adopted._adopt_node(node)
            assert node.getAttribute("aria-label") == "card"
            assert node.getAttribute("data-role") == "summary"

    def test_adopt_strips_stale_framework_markers(self) -> None:
        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(Card) as result:
            node = result._instance._node_cache
            assert node is not None
            node.setAttribute("webcompy-cid-stale", "true")
            node.setAttribute("aria-label", "card")
            adopted = Card(None)
            adopted._adopt_node(node)
            assert node.getAttribute("webcompy-cid-stale") is None
            assert node.getAttribute("aria-label") == "card"

    def test_unmounted_suppressed_while_node_connected(self) -> None:
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY

        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(Card) as result:
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
        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(Card) as result:
            instance = result._instance
            fired: list[str] = []
            instance._property["on_unmounted"] = lambda: fired.append("unmounted")
            instance._mount_delivered = True
            instance._detach_from_node()
            instance._remove_element()
            assert fired == []

    def test_detach_fires_unmount_when_node_disconnected(self) -> None:
        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with TestRenderer.render(Card) as result:
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

        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        @define_component
        def Root(context: ComponentContext[None]):
            card = Card(None)
            captured.append(card)
            return html.DIV({}, card)

        with TestRenderer.render(Root) as result:
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

        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with DIScope() as scope:
            scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
            scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())
            instance = Card(None)
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

        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        with DIScope() as scope:
            scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
            scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())
            scope.provide(CUSTOM_ELEMENT_PORT_KEY, FakeCustomElementPort())
            instance = Card(None)
            with pytest.raises(WebComPyComponentException, match="Host port"):
                instance._bind_custom_element(FakeDOMNode("my-card"))

    def test_ensure_defined_conflict_propagates(self) -> None:
        from webcompy.app._root_component import AppDocumentRoot
        from webcompy.components._generator import ComponentStore
        from webcompy.di import DIScope
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY
        from webcompy_testing import FakeCustomElementPort

        @define_component("my-card")
        def Card(context: ComponentContext[None]):
            return html.DIV({}, "card")

        class _ConflictPort(FakeCustomElementPort):
            def ensure_defined(self, name, observed_attributes, definition_key):
                raise WebComPyComponentException(
                    f"Custom element '{name}' is already defined with incompatible metadata"
                )

        store = ComponentStore()
        store.add_component("Card", Card)
        root = object.__new__(AppDocumentRoot)
        with DIScope() as scope:
            scope.provide(_COMPONENT_STORE_KEY, store)
            scope.provide(CUSTOM_ELEMENT_PORT_KEY, _ConflictPort())
            with pytest.raises(WebComPyComponentException, match="incompatible"):
                root._ensure_custom_elements_defined()
