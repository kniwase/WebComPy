from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from tests.conftest import (
    FakeBrowserDOMPort,
    FakeBrowserFFIPort,
    FakeBrowserHostPort,
    FakeDOMNode,
)
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements._bind import expand_bind_attr
from webcompy.elements.types._element import Element
from webcompy.exception import WebComPyException
from webcompy.ports._keys import DOM_PORT_KEY, FFI_PORT_KEY, HOST_PORT_KEY
from webcompy.signal import Computed, ReactiveDict, ReactiveList, Signal, readonly
from webcompy_server.ports import VirtualDOMEvent, VirtualDOMNode
from webcompy_server.ports._dom import ServerDOMPort


def _ev(value=None, *, checked=None, target=None):
    if target is None:
        target = SimpleNamespace()
        if value is not None:
            target.value = value
        if checked is not None:
            target.checked = checked
    return SimpleNamespace(target=target)


class TestKindValidation:
    @pytest.mark.parametrize("value", ["x", 5, False, None])
    def test_non_signal_rejected(self, value):
        with pytest.raises(WebComPyException, match="writable Signal"):
            expand_bind_attr("input", {":bind": value}, {})

    def test_computed_rejected(self):
        with pytest.raises(WebComPyException, match="writable Signal"):
            expand_bind_attr("input", {":bind": Computed(lambda: 1)}, {})

    def test_readonly_rejected(self):
        with pytest.raises(WebComPyException, match="writable Signal"):
            expand_bind_attr("input", {":bind": readonly(Signal("x"))}, {})

    def test_reactive_list_rejected(self):
        with pytest.raises(WebComPyException, match="writable Signal"):
            expand_bind_attr("input", {":bind": ReactiveList([1])}, {})

    def test_reactive_dict_rejected(self):
        with pytest.raises(WebComPyException, match="writable Signal"):
            expand_bind_attr("input", {":bind": ReactiveDict({"a": 1})}, {})


class TestTextBindings:
    def test_text_input_default_type(self):
        sig = Signal("hello")
        attrs = {":bind": sig}
        events = {}
        expand_bind_attr("input", attrs, events)
        assert ":bind" not in attrs
        assert attrs["value"] is sig
        assert "input" in events

    @pytest.mark.parametrize("input_type", ["text", "email", "password", "search", "tel", "url"])
    def test_text_input_explicit_type(self, input_type):
        sig = Signal("x")
        attrs = {"type": input_type, ":bind": sig}
        events = {}
        expand_bind_attr("input", attrs, events)
        assert attrs["value"] is sig
        assert attrs["type"] == input_type
        assert "input" in events

    def test_textarea(self):
        sig = Signal("hello")
        attrs = {":bind": sig}
        events = {}
        children: list = []
        expand_bind_attr("textarea", attrs, events, children)
        assert "value" not in attrs
        assert children == [sig]
        assert "input" in events

    def test_textarea_write_back_sets_signal(self):
        sig = Signal("hello")
        attrs = {":bind": sig}
        events = {}
        children: list = []
        expand_bind_attr("textarea", attrs, events, children)
        events["input"](_ev(value="world"))
        assert sig.value == "world"

    def test_textarea_requires_children_list(self):
        with pytest.raises(WebComPyException, match="children"):
            expand_bind_attr("textarea", {":bind": Signal("x")}, {})

    def test_write_back_sets_signal(self):
        sig = Signal("hello")
        attrs = {":bind": sig}
        events = {}
        expand_bind_attr("input", attrs, events)
        events["input"](_ev(value="world"))
        assert sig.value == "world"

    def test_write_back_target_none_guarded(self):
        sig = Signal("x")
        attrs = {":bind": sig}
        events = {}
        expand_bind_attr("input", attrs, events)
        events["input"](SimpleNamespace(target=None))
        assert sig.value == "x"

    def test_type_mismatch_rejected(self):
        with pytest.raises(WebComPyException, match="str-valued"):
            expand_bind_attr("input", {":bind": Signal(5)}, {})


class TestNumberBinding:
    def test_expansion(self):
        sig = Signal(5)
        attrs = {"type": "number", ":bind": sig}
        events = {}
        expand_bind_attr("input", attrs, events)
        assert attrs["value"] is sig
        assert "input" in events

    def test_write_back_int(self):
        sig = Signal(5)
        attrs = {"type": "number", ":bind": sig}
        events = {}
        expand_bind_attr("input", attrs, events)
        events["input"](_ev(value="42"))
        assert sig.value == 42
        assert isinstance(sig.value, int)

    def test_write_back_float(self):
        sig = Signal(0.5)
        attrs = {"type": "number", ":bind": sig}
        events = {}
        expand_bind_attr("input", attrs, events)
        events["input"](_ev(value="1.25"))
        assert sig.value == 1.25
        assert isinstance(sig.value, float)

    def test_write_back_empty_skipped(self):
        sig = Signal(5)
        attrs = {"type": "number", ":bind": sig}
        events = {}
        expand_bind_attr("input", attrs, events)
        events["input"](_ev(value=""))
        assert sig.value == 5

    def test_write_back_unparseable_skipped(self):
        sig = Signal(5)
        attrs = {"type": "number", ":bind": sig}
        events = {}
        expand_bind_attr("input", attrs, events)
        events["input"](_ev(value="abc"))
        assert sig.value == 5

    def test_write_back_float_on_int_signal_skipped(self):
        sig = Signal(5)
        attrs = {"type": "number", ":bind": sig}
        events = {}
        expand_bind_attr("input", attrs, events)
        events["input"](_ev(value="1.5"))
        assert sig.value == 5

    def test_str_valued_rejected(self):
        with pytest.raises(WebComPyException, match="int or float"):
            expand_bind_attr("input", {"type": "number", ":bind": Signal("x")}, {})

    def test_bool_valued_rejected(self):
        with pytest.raises(WebComPyException, match="int or float"):
            expand_bind_attr("input", {"type": "number", ":bind": Signal(True)}, {})


class TestCheckboxBinding:
    def test_expansion(self):
        flag = Signal(False)
        attrs = {"type": "checkbox", ":bind": flag}
        events = {}
        expand_bind_attr("input", attrs, events)
        assert attrs["checked"] is flag
        assert "change" in events

    def test_write_back(self):
        flag = Signal(False)
        attrs = {"type": "checkbox", ":bind": flag}
        events = {}
        expand_bind_attr("input", attrs, events)
        events["change"](_ev(checked=True))
        assert flag.value is True
        events["change"](_ev(checked=False))
        assert flag.value is False

    def test_non_bool_valued_rejected(self):
        with pytest.raises(WebComPyException, match="bool-valued"):
            expand_bind_attr("input", {"type": "checkbox", ":bind": Signal("x")}, {})


class TestRadioBinding:
    def test_expansion(self):
        choice = Signal("a")
        attrs = {":bind": choice, "value": "a", "type": "radio"}
        events = {}
        expand_bind_attr("input", attrs, events)
        assert isinstance(attrs["checked"], Computed)
        assert attrs["value"] == "a"
        assert attrs["checked"].value is True
        assert "change" in events

    def test_group_sync(self):
        choice = Signal("a")
        attrs_a = {":bind": choice, "value": "a", "type": "radio"}
        attrs_b = {":bind": choice, "value": "b", "type": "radio"}
        events_a: dict = {}
        events_b: dict = {}
        expand_bind_attr("input", attrs_a, events_a)
        expand_bind_attr("input", attrs_b, events_b)
        assert attrs_a["checked"].value is True
        assert attrs_b["checked"].value is False
        events_b["change"](_ev(checked=True))
        assert choice.value == "b"
        assert attrs_a["checked"].value is False
        assert attrs_b["checked"].value is True

    def test_write_back_unchecked_noop(self):
        choice = Signal("a")
        attrs = {":bind": choice, "value": "b", "type": "radio"}
        events: dict = {}
        expand_bind_attr("input", attrs, events)
        events["change"](_ev(checked=False))
        assert choice.value == "a"

    def test_missing_value_rejected(self):
        with pytest.raises(WebComPyException, match="static value"):
            expand_bind_attr("input", {"type": "radio", ":bind": Signal("a")}, {})

    def test_dynamic_value_rejected(self):
        with pytest.raises(WebComPyException, match="static value"):
            expand_bind_attr("input", {"type": "radio", ":bind": Signal("a"), "value": Signal("x")}, {})


class TestConflicts:
    def test_text_value_conflict(self):
        with pytest.raises(WebComPyException, match="'value'"):
            expand_bind_attr("input", {":bind": Signal("x"), "value": "y"}, {})

    def test_checkbox_checked_conflict(self):
        with pytest.raises(WebComPyException, match="'checked'"):
            expand_bind_attr("input", {"type": "checkbox", ":bind": Signal(False), "checked": True}, {})

    def test_radio_checked_conflict(self):
        with pytest.raises(WebComPyException, match="'checked'"):
            expand_bind_attr("input", {"type": "radio", ":bind": Signal("a"), "value": "a", "checked": True}, {})

    def test_textarea_children_conflict(self):
        with pytest.raises(WebComPyException, match="text content"):
            expand_bind_attr("textarea", {":bind": Signal("x")}, {}, ["default"])


class TestDynamicType:
    def test_dynamic_type_rejected(self):
        with pytest.raises(WebComPyException, match="static 'type'"):
            expand_bind_attr("input", {"type": Computed(lambda: "text"), ":bind": Signal("x")}, {})


class TestUnsupportedElements:
    @pytest.mark.parametrize(
        "tag,extra",
        [
            ("select", {}),
            ("option", {}),
            ("div", {}),
            ("input", {"type": "color"}),
            ("input", {"type": "date"}),
        ],
    )
    def test_unsupported_rejected(self, tag, extra):
        attrs = {":bind": Signal("x"), **extra}
        with pytest.raises(WebComPyException, match="not supported"):
            expand_bind_attr(tag, attrs, {})

    def test_message_names_supported_elements(self):
        with pytest.raises(WebComPyException, match="input"):
            expand_bind_attr("select", {":bind": Signal("x")}, {})


class TestHandlerChaining:
    def test_user_handler_runs_after_binding(self):
        sig = Signal("a")
        calls: list[tuple[str, str]] = []

        def user_handler(ev):
            calls.append(("user", sig.value))

        attrs = {":bind": sig}
        events = {"input": user_handler}
        expand_bind_attr("input", attrs, events)
        assert "input" in events
        events["input"](_ev(value="b"))
        assert sig.value == "b"
        assert calls == [("user", "b")]

    def test_async_user_handler_runs_after_binding(self):
        sig = Signal("a")
        calls: list[tuple[str, str]] = []

        async def user_handler(ev):
            calls.append(("user", sig.value))

        attrs = {":bind": sig}
        events = {"input": user_handler}
        expand_bind_attr("input", attrs, events)
        asyncio.run(events["input"](_ev(value="z")))
        assert sig.value == "z"
        assert calls == [("user", "z")]

    def test_unrelated_event_untouched(self):
        sig = Signal("a")

        def user_handler(ev):
            return None

        attrs = {":bind": sig}
        events = {"blur": user_handler}
        expand_bind_attr("input", attrs, events)
        assert events["blur"] is user_handler
        assert "input" in events


class _DummyParent:
    def __init__(self, node):
        self._node = node

    def _get_node(self):
        return self._node

    def _get_belonging_component(self):
        return ""

    def _get_belonging_components(self):
        return ()

    def _re_index_children(self, recursive):
        pass


async def _render_with_fake_browser(element):
    scope = DIScope()
    scope.provide(DOM_PORT_KEY, FakeBrowserDOMPort())
    scope.provide(HOST_PORT_KEY, FakeBrowserHostPort())
    scope.provide(FFI_PORT_KEY, FakeBrowserFFIPort())
    token = _active_di_scope.set(scope)
    try:
        root_node = FakeDOMNode("div")
        root_node.__webcompy_node__ = False
        root_node.__webcompy_prerendered_node__ = True
        element._parent = _DummyParent(root_node)
        element._node_idx = 0
        await element._render()
        if root_node.childNodes.length > 0:
            return root_node.childNodes[0]
        return None
    finally:
        _active_di_scope.reset(token)


async def _render_with_server(element):
    port = ServerDOMPort()
    scope = DIScope()
    scope.provide(DOM_PORT_KEY, port)
    scope.provide(HOST_PORT_KEY, FakeBrowserHostPort())
    scope.provide(FFI_PORT_KEY, FakeBrowserFFIPort())
    token = _active_di_scope.set(scope)
    try:
        root_node = VirtualDOMNode("div")
        root_node.__webcompy_node__ = False
        root_node.__webcompy_prerendered_node__ = True
        element._parent = _DummyParent(root_node)
        element._node_idx = 0
        await element._render()
        if root_node.childNodes.length > 0:
            return root_node.childNodes[0]
        return None
    finally:
        _active_di_scope.reset(token)


class TestElementIntegration:
    @pytest.mark.asyncio
    async def test_text_binding_initial_value(self):
        el = Element("input", {":bind": Signal("hello")}, {}, None, None)
        node = await _render_with_fake_browser(el)
        assert node.getAttribute("value") == "hello"

    @pytest.mark.asyncio
    async def test_no_bind_attribute_on_dom(self):
        el = Element("input", {":bind": Signal("hello")}, {}, None, None)
        node = await _render_with_fake_browser(el)
        assert node.getAttribute(":bind") is None

    @pytest.mark.asyncio
    async def test_dom_to_signal_write_back(self):
        sig = Signal("hello")
        el = Element("input", {":bind": sig}, {}, None, None)
        node = await _render_with_fake_browser(el)
        node.value = "world"
        node.dispatchEvent(VirtualDOMEvent("input"))
        assert sig.value == "world"

    @pytest.mark.asyncio
    async def test_signal_to_dom_update(self):
        sig = Signal("hello")
        el = Element("input", {":bind": sig}, {}, None, None)
        node = await _render_with_fake_browser(el)
        sig.value = "next"
        assert node.getAttribute("value") == "next"

    @pytest.mark.asyncio
    async def test_checkbox_binding(self):
        flag = Signal(False)
        el = Element("input", {"type": "checkbox", ":bind": flag}, {}, None, None)
        node = await _render_with_fake_browser(el)
        assert node.getAttribute("checked") is None
        node.checked = True
        node.dispatchEvent(VirtualDOMEvent("change"))
        assert flag.value is True
        assert node.getAttribute("checked") == ""

    @pytest.mark.asyncio
    async def test_radio_group_sync(self):
        choice = Signal("a")
        el = Element(
            "div",
            {},
            {},
            None,
            [
                Element("input", {"type": "radio", "value": "a", ":bind": choice}, {}, None, None),
                Element("input", {"type": "radio", "value": "b", ":bind": choice}, {}, None, None),
            ],
        )
        root = await _render_with_fake_browser(el)
        node_a = root.childNodes[0]
        node_b = root.childNodes[1]
        assert node_a.getAttribute("checked") == ""
        assert node_b.getAttribute("checked") is None
        node_b.checked = True
        node_b.dispatchEvent(VirtualDOMEvent("change"))
        assert choice.value == "b"
        assert node_a.getAttribute("checked") is None
        assert node_b.getAttribute("checked") == ""

    @pytest.mark.asyncio
    async def test_ssr_renders_bound_attr_only(self):
        el = Element("input", {":bind": Signal("hello")}, {}, None, None)
        node = await _render_with_server(el)
        html = ServerDOMPort().render_html(node)
        assert 'value="hello"' in html
        assert ":bind" not in html

    @pytest.mark.asyncio
    async def test_textarea_binding_text_content(self):
        sig = Signal("initial")
        el = Element("textarea", {":bind": sig}, {}, None, None)
        node = await _render_with_fake_browser(el)
        assert node.textContent == "initial"
        node.value = "typed"
        node.dispatchEvent(VirtualDOMEvent("input"))
        assert sig.value == "typed"
        sig.value = "next"
        assert node.textContent == "next"

    @pytest.mark.asyncio
    async def test_textarea_ssr_renders_text_content(self):
        el = Element("textarea", {":bind": Signal("initial")}, {}, None, None)
        node = await _render_with_server(el)
        html = ServerDOMPort().render_html(node)
        assert "<textarea>initial</textarea>" in html
