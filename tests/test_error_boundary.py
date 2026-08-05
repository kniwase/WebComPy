from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from webcompy.components import define_component
from webcompy.components._component import Component, _set_app_instance
from webcompy.di import DIScope
from webcompy.di._keys import ERROR_POLICY_KEY
from webcompy.elements import ErrorBoundary, html
from webcompy.elements.types._error_boundary import (
    ErrorBoundaryElement,
    report_unhandled_error,
    route_error,
)
from webcompy_testing import TestRenderer, run_sync


def _find_boundary(root) -> ErrorBoundaryElement | None:
    if isinstance(root, ErrorBoundaryElement):
        return root
    for child in getattr(root, "_children", None) or []:
        found = _find_boundary(child)
        if found is not None:
            return found
    return None


def _find_element_by_testid(root, testid: str):
    attrs = getattr(root, "_attrs", None) or {}
    if attrs.get("data-testid") == testid:
        return root
    for child in getattr(root, "_children", None) or []:
        found = _find_element_by_testid(child, testid)
        if found is not None:
            return found
    return None


def _find_component_by_name(root, name: str) -> Component | None:
    if isinstance(root, Component) and root._property.get("component_name") == name:
        return root
    for child in getattr(root, "_children", None) or []:
        found = _find_component_by_name(child, name)
        if found is not None:
            return found
    return None


class TestErrorBoundaryRender:
    def test_sync_setup_error_renders_fallback_and_calls_on_error(self):
        errors: list[Exception] = []

        @define_component
        def CrashingChild(context):
            raise RuntimeError("sync setup failed")

        @define_component
        def Root(context):
            return html.DIV(
                {"data-testid": "root"},
                ErrorBoundary(
                    children=lambda: CrashingChild(None),
                    fallback=lambda error, reset: html.DIV({"data-testid": "fallback"}, str(error)),
                    on_error=lambda e: errors.append(e),
                ),
                html.SPAN({"data-testid": "sibling"}, "alive"),
            )

        with TestRenderer.render(Root) as result:
            assert result.find_by_attribute("data-testid", "fallback") is not None
            assert result.find_by_text("sync setup failed") is not None
            assert result.find_by_attribute("data-testid", "sibling") is not None
            assert len(errors) == 1
            assert str(errors[0]) == "sync setup failed"
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            assert boundary._in_fallback

    def test_async_setup_error_renders_fallback(self):
        @define_component
        async def AsyncCrashingChild(context):
            await asyncio.sleep(0)
            raise RuntimeError("async setup failed")

        @define_component
        def Root(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: AsyncCrashingChild(None),
                    fallback=lambda error, reset: html.DIV({"data-testid": "async-fallback"}, str(error)),
                ),
            )

        with TestRenderer.render(Root) as result:
            assert result.find_by_attribute("data-testid", "async-fallback") is not None
            assert result.find_by_text("async setup failed") is not None
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            assert boundary._in_fallback

    def test_no_error_renders_children_normally(self):
        @define_component
        def HealthyChild(context):
            return html.DIV({"data-testid": "healthy"}, "ok")

        @define_component
        def Root(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: HealthyChild(None),
                    fallback=lambda error, reset: html.DIV({"data-testid": "fallback"}, "fb"),
                ),
            )

        with TestRenderer.render(Root) as result:
            assert result.find_by_attribute("data-testid", "healthy") is not None
            assert result.find_by_attribute("data-testid", "fallback") is None
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            assert not boundary._in_fallback

    def test_nested_boundaries_innermost_engages(self):
        @define_component
        def CrashingChild(context):
            raise RuntimeError("boom")

        @define_component
        def Root(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: ErrorBoundary(
                        children=lambda: CrashingChild(None),
                        fallback=lambda e, r: html.DIV({"data-testid": "inner-fallback"}, "inner"),
                    ),
                    fallback=lambda e, r: html.DIV({"data-testid": "outer-fallback"}, "outer"),
                ),
            )

        with TestRenderer.render(Root) as result:
            assert result.find_by_attribute("data-testid", "inner-fallback") is not None
            assert result.find_by_attribute("data-testid", "outer-fallback") is None

    def test_error_in_fallback_escalates_to_outer_boundary(self):
        @define_component
        def CrashingChild(context):
            raise RuntimeError("original boom")

        def failing_fallback(error: Exception, reset):
            raise RuntimeError("fallback failed")

        @define_component
        def Root(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: ErrorBoundary(
                        children=lambda: CrashingChild(None),
                        fallback=failing_fallback,
                    ),
                    fallback=lambda e, r: html.DIV({"data-testid": "outer-fallback"}, str(e)),
                ),
            )

        with TestRenderer.render(Root) as result:
            outer = result.find_by_attribute("data-testid", "outer-fallback")
            assert outer is not None
            assert "fallback failed" in (outer.textContent or "")

    def test_fallback_receives_error_and_reset_callable(self):
        captured: dict[str, object] = {}

        @define_component
        def CrashingChild(context):
            raise RuntimeError("capture me")

        def fallback(error: Exception, reset):
            captured["error"] = error
            captured["reset"] = reset
            return html.DIV({"data-testid": "capturing-fallback"}, "fb")

        @define_component
        def Root(context):
            return html.DIV({}, ErrorBoundary(children=lambda: CrashingChild(None), fallback=fallback))

        with TestRenderer.render(Root) as result:
            assert result.find_by_attribute("data-testid", "capturing-fallback") is not None
            error = captured["error"]
            assert isinstance(error, RuntimeError)
            assert str(error) == "capture me"
            assert callable(captured["reset"])


class TestPropagationWalk:
    def test_hooks_invoked_nearest_first_then_boundary_engages(self):
        calls: list[str] = []

        @define_component
        def InnerHookCmp(context):
            context.on_error_captured(lambda e: calls.append("inner"))
            return html.DIV({"data-testid": "inner-hook"}, "inner")

        @define_component
        def OuterHookCmp(context):
            context.on_error_captured(lambda e: calls.append("outer"))
            return html.DIV({}, InnerHookCmp(None))

        @define_component
        def Root(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: OuterHookCmp(None),
                    fallback=lambda e, r: html.DIV({"data-testid": "walk-fallback"}, "fb"),
                ),
            )

        with TestRenderer.render(Root) as result:
            source = _find_element_by_testid(result._instance, "inner-hook")
            assert source is not None
            run_sync(route_error(source, RuntimeError("walk error")))
            assert calls == ["inner", "outer"]
            assert result.find_by_attribute("data-testid", "walk-fallback") is not None
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            assert boundary._in_fallback

    def test_hook_veto_prevents_boundary_engagement(self):
        calls: list[str] = []

        @define_component
        def InnerHookCmp(context):
            def veto(e: Exception):
                calls.append("inner")
                return False

            context.on_error_captured(veto)
            return html.DIV({"data-testid": "inner-hook"}, "inner")

        @define_component
        def OuterHookCmp(context):
            context.on_error_captured(lambda e: calls.append("outer"))
            return html.DIV({}, InnerHookCmp(None))

        @define_component
        def Root(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: OuterHookCmp(None),
                    fallback=lambda e, r: html.DIV({"data-testid": "walk-fallback"}, "fb"),
                ),
            )

        with TestRenderer.render(Root) as result:
            source = _find_element_by_testid(result._instance, "inner-hook")
            assert source is not None
            run_sync(route_error(source, RuntimeError("vetoed")))
            assert calls == ["inner"]
            assert result.find_by_attribute("data-testid", "walk-fallback") is None
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            assert not boundary._in_fallback

    def test_hooks_above_engaged_boundary_not_invoked(self):
        calls: list[str] = []

        @define_component
        def CrashingChild(context):
            raise RuntimeError("boom")

        @define_component
        def Root(context):
            context.on_error_captured(lambda e: calls.append("root"))
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: CrashingChild(None),
                    fallback=lambda e, r: html.DIV({"data-testid": "fallback"}, "fb"),
                ),
            )

        with TestRenderer.render(Root) as result:
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            assert boundary._in_fallback
            assert calls == []

    def test_destroyed_component_hooks_not_invoked(self):
        calls: list[str] = []

        @define_component
        def InnerHookCmp(context):
            context.on_error_captured(lambda e: calls.append("inner"))
            return html.DIV({"data-testid": "inner-hook"}, "inner")

        @define_component
        def OuterHookCmp(context):
            context.on_error_captured(lambda e: calls.append("outer"))
            return html.DIV({}, InnerHookCmp(None))

        @define_component
        def Root(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: OuterHookCmp(None),
                    fallback=lambda e, r: html.DIV({"data-testid": "walk-fallback"}, "fb"),
                ),
            )

        with TestRenderer.render(Root) as result:
            inner_cmp = _find_component_by_name(result._instance, "InnerHookCmp")
            assert inner_cmp is not None
            source = _find_element_by_testid(result._instance, "inner-hook")
            assert source is not None
            inner_cmp._remove_element()
            run_sync(route_error(source, RuntimeError("after destroy")))
            assert calls == ["outer"]


class TestReset:
    def test_reset_rebuilds_children_with_fresh_state(self):
        state = {"crash": True, "setup_count": 0}

        @define_component
        def FlakyChild(context):
            state["setup_count"] += 1
            if state["crash"]:
                raise RuntimeError("flaky failure")
            return html.DIV({"data-testid": "flaky-ok"}, f"ok-{state['setup_count']}")

        @define_component
        def Root(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: FlakyChild(None),
                    fallback=lambda e, r: html.DIV({"data-testid": "flaky-fallback"}, "fb"),
                ),
            )

        with TestRenderer.render(Root) as result:
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            assert boundary._in_fallback
            assert result.find_by_attribute("data-testid", "flaky-fallback") is not None
            assert state["setup_count"] == 1

            state["crash"] = False
            run_sync(boundary._do_reset())

            assert not boundary._in_fallback
            assert boundary._error is None
            assert state["setup_count"] == 2
            assert result.find_by_attribute("data-testid", "flaky-ok") is not None
            assert result.find_by_attribute("data-testid", "flaky-fallback") is None

    def test_reset_with_persistent_error_reengages_fallback(self):
        state = {"setup_count": 0}

        @define_component
        def AlwaysCrashing(context):
            state["setup_count"] += 1
            raise RuntimeError("persistent failure")

        @define_component
        def Root(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: AlwaysCrashing(None),
                    fallback=lambda e, r: html.DIV({"data-testid": "persistent-fallback"}, str(e)),
                ),
            )

        with TestRenderer.render(Root) as result:
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            assert boundary._in_fallback
            assert state["setup_count"] == 1

            run_sync(boundary._do_reset())

            assert boundary._in_fallback
            assert state["setup_count"] == 2
            assert result.find_by_attribute("data-testid", "persistent-fallback") is not None

    def test_sync_reset_entry_point_schedules_refresh(self):
        state = {"crash": True}

        @define_component
        def FlakyChild(context):
            if state["crash"]:
                raise RuntimeError("flaky failure")
            return html.DIV({"data-testid": "flaky-ok"}, "ok")

        @define_component
        def Root(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: FlakyChild(None),
                    fallback=lambda e, r: html.DIV({"data-testid": "flaky-fallback"}, "fb"),
                ),
            )

        with TestRenderer.render(Root) as result:
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            assert boundary._in_fallback
            state["crash"] = False
            boundary.reset()
            assert not boundary._in_fallback
            assert result.find_by_attribute("data-testid", "flaky-ok") is not None

    def test_reset_noop_when_not_in_fallback(self):
        @define_component
        def HealthyChild(context):
            return html.DIV({"data-testid": "healthy"}, "ok")

        @define_component
        def Root(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: HealthyChild(None),
                    fallback=lambda e, r: html.DIV({"data-testid": "fallback"}, "fb"),
                ),
            )

        with TestRenderer.render(Root) as result:
            boundary = _find_boundary(result._instance)
            assert boundary is not None
            run_sync(boundary._do_reset())
            assert not boundary._in_fallback
            assert result.find_by_attribute("data-testid", "healthy") is not None


class TestErrorPolicy:
    def test_ssg_policy_reraises_original_error(self):
        @define_component
        def CrashingChild(context):
            raise RuntimeError("ssg crash")

        @define_component
        def Root(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: CrashingChild(None),
                    fallback=lambda e, r: html.DIV({}, "fb"),
                ),
            )

        scope = DIScope()
        scope.provide(ERROR_POLICY_KEY, "ssg")
        try:
            with pytest.raises(RuntimeError, match="ssg crash"):
                TestRenderer.render(Root, parent_scope=scope)
        finally:
            scope.dispose()

    def test_default_policy_is_ssr_tolerant(self):
        @define_component
        def CrashingChild(context):
            raise RuntimeError("ssr crash")

        @define_component
        def Root(context):
            return html.DIV(
                {},
                ErrorBoundary(
                    children=lambda: CrashingChild(None),
                    fallback=lambda e, r: html.DIV({"data-testid": "ssr-fallback"}, "fb"),
                ),
            )

        with TestRenderer.render(Root) as result:
            assert result.find_by_attribute("data-testid", "ssr-fallback") is not None


class TestGlobalHandler:
    def test_unhandled_error_reaches_config_on_error(self):
        received: list[Exception] = []
        fake_ctx = SimpleNamespace(_config=SimpleNamespace(on_error=received.append))
        _set_app_instance(fake_ctx)
        try:
            err = RuntimeError("uncontained")
            run_sync(route_error(None, err))
        finally:
            _set_app_instance(None)
        assert received == [err]

    def test_report_unhandled_calls_config_handler_once(self):
        received: list[Exception] = []
        fake_ctx = SimpleNamespace(_config=SimpleNamespace(on_error=received.append))
        _set_app_instance(fake_ctx)
        try:
            err = RuntimeError("reported")
            report_unhandled_error(err)
        finally:
            _set_app_instance(None)
        assert received == [err]

    def test_handler_exception_is_swallowed(self):
        def bad_handler(e: Exception):
            raise ValueError("handler exploded")

        fake_ctx = SimpleNamespace(_config=SimpleNamespace(on_error=bad_handler))
        _set_app_instance(fake_ctx)
        try:
            report_unhandled_error(RuntimeError("original"))
        finally:
            _set_app_instance(None)

    def test_default_logging_without_handler(self, monkeypatch):
        logged: list[Exception] = []
        monkeypatch.setattr("webcompy.aio._aio._log_error", lambda e: logged.append(e))
        _set_app_instance(None)
        err = RuntimeError("logged")
        report_unhandled_error(err)
        assert logged == [err]
