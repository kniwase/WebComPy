from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import pytest

from webcompy.components._component import Component, HeadPropsStore
from webcompy.components._generator import (
    ComponentGenerator,
    ComponentStore,
    define_component,
)
from webcompy.di import _pending_di_parent
from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._text import NewLine, TextElement
from webcompy.exception import WebComPyException
from webcompy.signal import Computed, Signal
from webcompy.template._binder import bind_element
from webcompy.template._parser import parse_template


@contextmanager
def _component_di_scope() -> Any:
    store = ComponentStore()
    head_props = HeadPropsStore()
    parent_scope = _active_di_scope.get(None)
    if parent_scope is not None and getattr(parent_scope, "_disposed", False):
        parent_scope = None
    scope = parent_scope.create_child() if parent_scope is not None else DIScope()
    scope.provide(_COMPONENT_STORE_KEY, store)
    scope.provide(_HEAD_PROPS_KEY, head_props)
    di_token = _active_di_scope.set(scope)
    pending_token = _pending_di_parent.set(scope)
    try:
        yield scope, store
    finally:
        _pending_di_parent.reset(pending_token)
        _active_di_scope.reset(di_token)
        scope.dispose()


def _make_recorder(name: str, captured: dict[str, Any]) -> ComponentGenerator[Any]:
    """Create a generator inside the active scope; auto-registers itself.

    The captured dict receives the ``props`` (raw dict) and ``slots`` (raw
    dict of NodeGenerator callables, copied from the Context's name-mangled
    private ``__slots``). Both are inspected directly to avoid having to call
    ``ctx.slots(name)`` which renders content and logs warnings on misses.
    """

    def setup(ctx: Any) -> Element:
        captured["props"] = ctx.props
        captured["slots"] = ctx._Context__slots
        return Element("span", {}, [], None, ["ok"])

    return ComponentGenerator(name, setup, custom_element_name=f"x-{name.lower()}")


def _bind(source: str, ctx: dict[str, Any] | None = None) -> Any:
    roots = parse_template(source)
    return bind_element(roots[0], ctx or {})


class TestComponentTagResolution:
    def test_kebab_resolves_to_registered_component(self):
        captured: dict[str, Any] = {}
        with _component_di_scope():
            _make_recorder("UserCard", captured)
            _bind("<user-card title='Hi' />")
        assert captured["props"] == {"title": "Hi"}
        assert captured["slots"] == {}

    def test_kebab_missing_component_raises_with_available_list(self):
        with _component_di_scope():
            _make_recorder("Navbar", {})
            _make_recorder("Footer", {})
            with pytest.raises(WebComPyException) as exc_info:
                _bind("<user-card />")
        message = str(exc_info.value)
        assert "UserCard" in message
        assert "<user-card>" in message
        assert "Navbar" in message
        assert "Footer" in message

    def test_lowercase_unknown_tag_falls_back_to_html(self):
        with _component_di_scope():
            _make_recorder("Widget", {})
            result = _bind("<widget>body</widget>")
        assert isinstance(result, Element)
        assert result._tag_name == "widget"
        assert result._children[0]._text == "body"


class TestSelfClosingComponentTag:
    def test_self_closing_yields_no_slot(self):
        captured: dict[str, Any] = {}
        with _component_di_scope():
            _make_recorder("UserCard", captured)
            _bind("<user-card title='Hi' />")
        assert captured["props"] == {"title": "Hi"}
        assert captured["slots"] == {}

    def test_paired_tag_passes_body_in_default_slot(self):
        captured: dict[str, Any] = {}
        with _component_di_scope():
            _make_recorder("UserCard", captured)
            _bind("<user-card><span>hi</span></user-card>")
        assert "default" in captured["slots"]
        rendered = captured["slots"]["default"]()
        assert isinstance(rendered, Element)
        assert rendered._tag_name == "span"
        assert isinstance(rendered._children[0], TextElement)
        assert rendered._children[0]._text == "hi"


class TestPropBinding:
    def test_static_prop_literal_string(self):
        captured: dict[str, Any] = {}
        with _component_di_scope():
            _make_recorder("UserCard", captured)
            _bind("<user-card title='Hello' />")
        assert captured["props"] == {"title": "Hello"}

    def test_dynamic_prop_preserves_signal(self):
        sig = Signal(5)
        captured: dict[str, Any] = {}
        with _component_di_scope():
            _make_recorder("UserCard", captured)
            _bind("<user-card :count='val' />", {"val": sig})
        assert captured["props"] == {"count": sig}

    def test_dynamic_prop_resolves_plain_value(self):
        captured: dict[str, Any] = {}
        with _component_di_scope():
            _make_recorder("UserCard", captured)
            _bind("<user-card :count='val' />", {"val": 99})
        assert captured["props"] == {"count": 99}

    def test_bind_prop_stays_plain_prop(self):
        sig = Signal(5)
        captured: dict[str, Any] = {}
        with _component_di_scope():
            _make_recorder("UserCard", captured)
            _bind("<user-card :bind='val' />", {"val": sig})
        assert captured["props"] == {"bind": sig}

    def test_kebab_prop_name_converts_to_snake(self):
        captured: dict[str, Any] = {}
        with _component_di_scope():
            _make_recorder("KCard", captured)
            _bind(
                '<k-card :item-count="n" :data-foo-bar="b" />',
                {"n": 1, "b": "x"},
            )
        assert captured["props"] == {"item_count": 1, "data_foo_bar": "x"}

    def test_interpolation_with_signal_produces_reactive_computed(self):
        captured: dict[str, Any] = {}
        with _component_di_scope():
            _make_recorder("UserCard", captured)
            name = Signal("Alice")
            _bind("<user-card title='Hello {{ name }}' />", {"name": name})
        title = captured["props"]["title"]
        assert isinstance(title, Computed)
        assert title.value == "Hello Alice"

        name.value = "Bob"
        assert title.value == "Hello Bob"

    def test_interpolation_static_when_no_signal(self):
        captured: dict[str, Any] = {}
        with _component_di_scope():
            _make_recorder("UserCard", captured)
            _bind("<user-card title='Hello {{ name }}' />", {"name": "Alice"})
        assert captured["props"]["title"] == "Hello Alice"

    def test_boolean_prop(self):
        captured: dict[str, Any] = {}
        with _component_di_scope():
            _make_recorder("BoolCard", captured)
            _bind("<bool-card disabled />")
        assert captured["props"] == {"disabled": True}


class TestDefaultSlot:
    def test_single_child_passes_through(self):
        captured: dict[str, Any] = {}
        with _component_di_scope():
            _make_recorder("MyWrapper", captured)
            _bind("<my-wrapper><p>x</p></my-wrapper>")
        rendered = captured["slots"]["default"]()
        assert isinstance(rendered, Element)
        assert rendered._tag_name == "p"

    def test_multiple_children_wrap_in_fragment(self):
        captured: dict[str, Any] = {}
        with _component_di_scope():
            _make_recorder("MyWrapper", captured)
            _bind("<my-wrapper><p>a</p><p>b</p></my-wrapper>")
        rendered = captured["slots"]["default"]()
        assert isinstance(rendered, FragmentElement)


class TestHtmlTagsUnaffected:
    def test_div_unchanged(self):
        with _component_di_scope():
            result = _bind("<div><p>text</p></div>")
        assert isinstance(result, Element)
        assert result._tag_name == "div"
        inner = result._children[0]
        assert isinstance(inner, Element)
        assert inner._tag_name == "p"
        assert inner._children[0]._text == "text"

    def test_p_with_text(self):
        with _component_di_scope():
            result = _bind("<p>hi</p>")
        assert isinstance(result, Element)
        assert result._tag_name == "p"


class TestBrStillNewLine:
    def test_br_short_circuits(self):
        with _component_di_scope():
            result = _bind("<br />")
        assert isinstance(result, NewLine)

    def test_br_does_not_trigger_component_lookup(self):
        with _component_di_scope():
            _make_recorder("Br", {})
            result = _bind("<br />")
        assert isinstance(result, NewLine)


class TestRealComponentEndToEnd:
    """End-to-end: ``@define_component`` + binder renders a ``Component``."""

    def test_define_component_runs_via_template_tag(self):
        @define_component("user-card")
        def UserCard(context):
            title = context.props.get("title", "")
            return Element("section", {}, [], None, [f"Card:{title}"])

        with _component_di_scope():
            UserCard._try_register()
            bound = _bind("<user-card title='Hi' />")
        assert isinstance(bound, Component)
