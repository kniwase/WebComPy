from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from webcompy.components import define_component, on_after_rendering, on_before_destroy, on_before_rendering
from webcompy.components._component import _active_app_context, _set_app_instance
from webcompy.elements import ErrorBoundary, Transition, html
from webcompy.elements.generators import repeat, suspense, switch
from webcompy.elements.types._error_boundary import ErrorBoundaryElement
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
from webcompy.signal import use_computed, use_reactive_list, use_state
from webcompy_testing import TestRenderer, run_sync


def _find_boundary(root) -> ErrorBoundaryElement | None:
    if isinstance(root, ErrorBoundaryElement):
        return root
    for child in getattr(root, "_children", None) or []:
        found = _find_boundary(child)
        if found is not None:
            return found
    return None


class TestReactiveRerenderErrors:
    def test_repeat_refresh_error_engages_boundary_and_app_stays_reactive(self):
        captured: dict[str, object] = {}

        def render_item(v: str):
            if v == "bad":
                raise RuntimeError("repeat refresh boom")
            return html.LI({"data-testid": f"item-{v}"}, v)

        @define_component("test-root")
        def TestRoot(context):
            items = use_reactive_list(lambda: ["a"])
            counter = use_state(lambda: 0)
            captured["items"] = items
            captured["counter"] = counter
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: html.UL({}, repeat(items, render_item)),
                    fallback=lambda e, r: html.DIV({"data-testid": "repeat-fallback"}, str(e)),
                ),
                html.SPAN({"data-testid": "counter"}, counter),
            )

        with TestRenderer.render(TestRoot) as result:
            assert result.find_by_attribute("data-testid", "item-a") is not None

            captured["items"].append("bad")
            scheduler = result._scope.inject(ASYNC_SCHEDULER_PORT_KEY)
            run_sync(scheduler.drain())

            assert result.find_by_attribute("data-testid", "repeat-fallback") is not None
            assert result.find_by_text("repeat refresh boom") is not None
            assert result.find_by_attribute("data-testid", "item-a") is None

            captured["counter"].value = 5
            assert result.find_by_text("5") is not None

    def test_switch_refresh_error_engages_boundary(self):
        captured: dict[str, object] = {}

        def bad_branch():
            raise RuntimeError("switch refresh boom")

        @define_component("test-root")
        def TestRoot(context):
            mode = use_state(lambda: "ok")
            captured["mode"] = mode
            is_ok = use_computed(lambda: mode.value == "ok")
            is_bad = use_computed(lambda: mode.value == "bad")
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: switch(
                        {"case": is_ok, "generator": lambda: html.DIV({"data-testid": "switch-ok"}, "ok")},
                        {"case": is_bad, "generator": bad_branch},
                    ),
                    fallback=lambda e, r: html.DIV({"data-testid": "switch-fallback"}, str(e)),
                ),
            )

        with TestRenderer.render(TestRoot) as result:
            assert result.find_by_attribute("data-testid", "switch-ok") is not None

            captured["mode"].value = "bad"
            scheduler = result._scope.inject(ASYNC_SCHEDULER_PORT_KEY)
            run_sync(scheduler.drain())

            assert result.find_by_attribute("data-testid", "switch-fallback") is not None
            assert result.find_by_text("switch refresh boom") is not None

    def test_transition_refresh_error_engages_boundary(self):
        captured: dict[str, object] = {}

        def bad_generator():
            raise RuntimeError("transition refresh boom")

        @define_component("test-root")
        def TestRoot(context):
            crash = use_state(lambda: False)
            captured["crash"] = crash
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: Transition(
                        {"name": "fade"},
                        lambda: bad_generator() if crash.value else html.DIV({"data-testid": "transition-ok"}, "ok"),
                    ),
                    fallback=lambda e, r: html.DIV({"data-testid": "transition-fallback"}, str(e)),
                ),
            )

        with TestRenderer.render(TestRoot) as result:
            assert result.find_by_attribute("data-testid", "transition-ok") is not None

            scheduler = result._scope.inject(ASYNC_SCHEDULER_PORT_KEY)

            async def _flip_and_drain() -> None:
                captured["crash"].value = True
                await scheduler.drain()

            run_sync(_flip_and_drain())

            assert result.find_by_attribute("data-testid", "transition-fallback") is not None
            assert result.find_by_text("transition refresh boom") is not None
            assert result.find_by_attribute("data-testid", "transition-ok") is None


class TestLifecycleHookErrors:
    def test_on_before_rendering_error_engages_boundary(self):
        captured: dict[str, object] = {}

        @define_component("hook-crashing")
        def HookCrashing(context):
            @on_before_rendering
            def hook():
                raise RuntimeError("before render boom")

            @on_after_rendering
            def after():
                captured["after"] = True

            return html.DIV({"data-testid": "hook-content"}, "content")

        @define_component("test-root")
        def TestRoot(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: HookCrashing(None),
                    fallback=lambda e, r: html.DIV({"data-testid": "lifecycle-fallback"}, str(e)),
                ),
            )

        with TestRenderer.render(TestRoot) as result:
            assert result.find_by_attribute("data-testid", "lifecycle-fallback") is not None
            assert result.find_by_text("before render boom") is not None
            assert result.find_by_attribute("data-testid", "hook-content") is None
            assert "after" not in captured

    def test_on_before_destroy_error_does_not_break_fallback_swap(self):
        received: list[Exception] = []
        fake_ctx = SimpleNamespace(_config=SimpleNamespace(on_error=received.append))

        @define_component("destroy-crashing")
        def DestroyCrashing(context):
            @on_before_destroy
            def hook():
                raise RuntimeError("destroy boom")

            return html.DIV({"data-testid": "destroy-content"}, "content")

        @define_component("test-root")
        def TestRoot(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: DestroyCrashing(None),
                    fallback=lambda e, r: html.DIV({"data-testid": "destroy-fallback"}, "fb"),
                ),
            )

        with TestRenderer.render(TestRoot) as result:
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            token = _active_app_context.set(None)
            _set_app_instance(fake_ctx)
            try:
                run_sync(boundary._engage(RuntimeError("trigger")))
            finally:
                _set_app_instance(None)
                _active_app_context.reset(token)
            assert boundary._in_fallback
            assert result.find_by_attribute("data-testid", "destroy-fallback") is not None
            assert result.find_by_attribute("data-testid", "destroy-content") is None
            assert any(str(e) == "destroy boom" for e in received)


class TestSuspenseErrorRouting:
    def test_suspense_server_error_propagates_to_boundary(self):
        @define_component("async-crashing")
        async def AsyncCrashing(context):
            await asyncio.sleep(0)
            raise RuntimeError("suspense child boom")

        @define_component("test-root")
        def TestRoot(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: suspense(
                        fallback=lambda: html.P({}, "loading"),
                        children=lambda: AsyncCrashing(None),
                    ),
                    fallback=lambda e, r: html.DIV({"data-testid": "suspense-fallback"}, str(e)),
                ),
            )

        with TestRenderer.render(TestRoot) as result:
            assert result.find_by_attribute("data-testid", "suspense-fallback") is not None
            assert result.find_by_text("suspense child boom") is not None

    @pytest.mark.asyncio
    async def test_suspense_browser_error_routes_to_boundary(self, monkeypatch):
        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")

        @define_component("async-crashing")
        async def AsyncCrashing(context):
            await asyncio.sleep(0)
            raise RuntimeError("browser suspense boom")

        @define_component("test-root")
        def TestRoot(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: suspense(
                        fallback=lambda: html.P({}, "loading"),
                        children=lambda: AsyncCrashing(None),
                    ),
                    fallback=lambda e, r: html.DIV({"data-testid": "suspense-fallback"}, str(e)),
                ),
            )

        with TestRenderer.render(TestRoot) as result:
            scheduler = result._scope.inject(ASYNC_SCHEDULER_PORT_KEY)
            await scheduler.drain()
            assert result.find_by_attribute("data-testid", "suspense-fallback") is not None
            assert result.find_by_text("browser suspense boom") is not None
