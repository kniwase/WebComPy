"""Tests for use_window_event() / use_document_event() composables."""

from __future__ import annotations

import html as html_module
import json
import logging as std_logging
import re
import warnings
from typing import Any

from webcompy import use_computed, use_document_event, use_window_event
from webcompy.components import define_component
from webcompy.components._context_manager import ComponentRenderState, component_context
from webcompy.components._hooks import on_before_destroy
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements import html
from webcompy.ports._keys import DOM_PORT_KEY, HOST_PORT_KEY
from webcompy.signal._effect import EffectScope
from webcompy_testing import FakeBrowserHostPort, TestRenderer


class FakeCtx:
    def __init__(self, name: str = "TestComp") -> None:
        self._component_name = name
        self._transferable_signals: dict = {}


def make_state(component_name: str = "TestComp") -> ComponentRenderState:
    return ComponentRenderState(
        context=FakeCtx(component_name),
        effect_scope=EffectScope(),
        framework_cleanup=lambda: None,
    )


class TestWindowEvent:
    def test_transform_updates_signal_and_notifies_consumers(self):
        @define_component
        def Page(context):
            width, _ = use_window_event("resize", 0, transform=lambda e: e["innerWidth"])
            label = use_computed(lambda: str(width.value))
            return html.DIV({}, html.SPAN({"data-testid": "w"}, label))

        with TestRenderer.render(Page) as result:
            host = result._scope.inject(HOST_PORT_KEY)
            el = result.find_by_attribute("data-testid", "w")
            assert el is not None and el.textContent == "0"
            host.dispatch_window_event("resize", {"innerWidth": 800})
            assert el.textContent == "800"

    def test_repeating_width_produces_no_notification(self):
        captured: dict[str, Any] = {}

        @define_component
        def Page(context):
            width, _ = use_window_event("resize", 0, transform=lambda e: e["innerWidth"])
            captured["width"] = width
            return html.DIV({}, "page")

        notified: list[int] = []
        with TestRenderer.render(Page) as result:
            host = result._scope.inject(HOST_PORT_KEY)
            captured["width"].on_after_updating(lambda v: notified.append(v))
            host.dispatch_window_event("resize", {"innerWidth": 800})
            host.dispatch_window_event("resize", {"innerWidth": 800})
        assert notified == [800]

    def test_single_listener_per_component_instance(self):
        @define_component
        def Page(context):
            width, _ = use_window_event("resize", 0, transform=lambda e: e["innerWidth"])
            return html.DIV({}, str(width.value))

        with TestRenderer.render(Page) as result:
            host = result._scope.inject(HOST_PORT_KEY)
            assert len(host._window_listeners.get("resize", [])) == 1

    def test_component_destroy_removes_listener(self):
        @define_component
        def Page(context):
            width, _ = use_window_event("resize", 0, transform=lambda e: e["innerWidth"])
            return html.DIV({}, str(width.value))

        with TestRenderer.render(Page) as result:
            host = result._scope.inject(HOST_PORT_KEY)
            assert len(host._window_listeners.get("resize", [])) == 1
            result._instance._remove_element()
            assert host._window_listeners.get("resize") == []

    def test_no_update_after_destroy(self):
        captured: dict[str, Any] = {}

        @define_component
        def Page(context):
            width, _ = use_window_event("resize", 0, transform=lambda e: e["innerWidth"])
            captured["width"] = width
            return html.DIV({}, "page")

        with TestRenderer.render(Page) as result:
            host = result._scope.inject(HOST_PORT_KEY)
            result._instance._remove_element()
            host.dispatch_window_event("resize", {"innerWidth": 800})
        assert captured["width"].value == 0


class TestDocumentEvent:
    def test_document_event_updates_signal(self):
        @define_component
        def Page(context):
            visibility, _ = use_document_event("visibilitychange", "visible", transform=lambda e: e["state"])
            label = use_computed(lambda: str(visibility.value))
            return html.DIV({}, html.SPAN({"data-testid": "v"}, label))

        with TestRenderer.render(Page) as result:
            dom = result._scope.inject(DOM_PORT_KEY)
            el = result.find_by_attribute("data-testid", "v")
            assert el is not None and el.textContent == "visible"
            dom.dispatch_document_event("visibilitychange", {"state": "hidden"})
            assert el.textContent == "hidden"

    def test_component_destroy_removes_document_listener(self):
        @define_component
        def Page(context):
            visibility, _ = use_document_event("visibilitychange", "visible")
            return html.DIV({}, str(visibility.value))

        with TestRenderer.render(Page) as result:
            dom = result._scope.inject(DOM_PORT_KEY)
            assert len(dom._document_listeners.get("visibilitychange", [])) == 1
            result._instance._remove_element()
            assert dom._document_listeners.get("visibilitychange") == []


class TestLifecycleGuarantees:
    def test_outside_setup_emits_warning_and_attaches_nothing(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            view, _update = use_window_event("resize", 0)
        assert any(issubclass(x.category, UserWarning) and "outside component setup" in str(x.message) for x in w)
        assert view.value == 0

    def test_outside_setup_with_active_di_scope_still_attaches_nothing(self):
        from webcompy_testing import FakeBrowserDOMPort

        host = FakeBrowserHostPort()
        dom = FakeBrowserDOMPort()
        scope = DIScope()
        scope.provide(HOST_PORT_KEY, host)
        scope.provide(DOM_PORT_KEY, dom)
        token = _active_di_scope.set(scope)
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                view, _update = use_document_event("visibilitychange", "visible")
        finally:
            _active_di_scope.reset(token)
        assert any(issubclass(x.category, UserWarning) for x in w)
        assert dom._document_listeners.get("visibilitychange", []) == []
        assert view.value == "visible"

    def test_missing_port_keeps_initial_without_warning(self):
        state = make_state()
        scope = DIScope()
        token = _active_di_scope.set(scope)
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                with component_context(state):
                    view, update = use_window_event("resize", 0)
        finally:
            _active_di_scope.reset(token)
        assert view.value == 0
        assert not [x for x in w if issubclass(x.category, UserWarning)]
        update(5)
        assert view.value == 5

    def test_transform_exception_is_contained(self, caplog):
        captured: dict[str, Any] = {}

        def _broken_transform(e: dict[str, int]) -> int:
            return e["innerWidth"] // 0

        @define_component
        def Page(context):
            width, _ = use_window_event("resize", 0, transform=_broken_transform)
            captured["width"] = width
            return html.DIV({}, "page")

        with TestRenderer.render(Page) as result:
            host = result._scope.inject(HOST_PORT_KEY)
            with caplog.at_level(std_logging.WARNING, logger="uvicorn"):
                host.dispatch_window_event("resize", {"innerWidth": 800})
            assert any("transform" in r.message for r in caplog.records)
            assert captured["width"].value == 0

    def test_chaining_with_existing_destroy_hook(self):
        order: list[str] = []

        @define_component
        def Page(context):
            @on_before_destroy
            def _user_hook():
                order.append("user")

            width, _ = use_window_event("resize", 0, transform=lambda e: e["innerWidth"])
            return html.DIV({}, str(width.value))

        with TestRenderer.render(Page) as result:
            host = result._scope.inject(HOST_PORT_KEY)
            result._instance._remove_element()
        assert order == ["user"]
        assert host._window_listeners.get("resize") == []


class TestSsrBehavior:
    def _generate(self, root) -> str:
        from webcompy_testing import create_test_app, render_app_html

        app = create_test_app(root_component=root)
        return render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )

    def test_ssr_renders_initial_without_warning(self):
        @define_component
        def Page(context):
            width, _ = use_window_event("resize", 0, transform=lambda e: e["innerWidth"])
            return html.DIV({"data-testid": "w"}, str(width.value))

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            html_str = self._generate(Page)
        assert not [x for x in w if issubclass(x.category, UserWarning)]
        assert 'data-testid="w"' in html_str
        assert ">0<" in html_str

    def test_ssr_payload_contains_no_readonly_state(self):
        @define_component
        def Page(context):
            width, _ = use_window_event("resize", 0, transform=lambda e: e["innerWidth"])
            label = use_computed(lambda: str(width.value))
            return html.DIV({}, label)

        html_str = self._generate(Page)
        match = re.search(
            r'<script type="application/json" id="__webcompy_data__">(.*?)</script>',
            html_str,
            re.DOTALL,
        )
        assert match is not None
        payload = json.loads(html_module.unescape(match.group(1)))
        assert payload["signals"] == {}
