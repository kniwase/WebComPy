from __future__ import annotations

import asyncio
import contextlib

import pytest

from webcompy.components._generator import define_component
from webcompy.components._hooks import (
    _active_component_context,
    on_after_rendering,
    on_before_destroy,
    on_before_rendering,
    use_async_result,
)
from webcompy.elements import html
from webcompy.elements.generators import suspense
from webcompy.signal import Signal, effect
from webcompy.signal._effect import _active_scope
from webcompy_testing import TestRenderer


class TestAsyncComponentContextActive:
    def test_active_component_context_available_in_async_body(self):
        captured = []

        @define_component
        async def AsyncCtxCmp(context):
            captured.append(_active_component_context.get())
            return html.DIV({}, "async")

        with TestRenderer.render(AsyncCtxCmp) as result:
            assert len(captured) == 1
            assert captured[0] is result._instance._render_state.context

    def test_active_scope_available_in_async_body(self):
        captured = []

        @define_component
        async def AsyncScopeCmp(context):
            captured.append(_active_scope.get())
            return html.DIV({}, "async")

        with TestRenderer.render(AsyncScopeCmp) as result:
            assert len(captured) == 1
            assert captured[0] is result._instance._render_state.effect_scope


class TestAsyncComponentLifecycleHooks:
    def test_async_body_on_before_rendering_hook_fires(self):
        called = []

        @define_component
        async def AsyncHookCmp(context):
            @on_before_rendering
            def hook():
                called.append("before")

            return html.DIV({}, "async")

        with TestRenderer.render(AsyncHookCmp):
            assert "before" in called

    def test_async_body_on_after_rendering_hook_fires(self):
        called = []

        @define_component
        async def AsyncHookCmp(context):
            @on_after_rendering
            def hook():
                called.append("after")

            return html.DIV({}, "async")

        with TestRenderer.render(AsyncHookCmp):
            assert "after" in called

    def test_async_body_on_before_destroy_hook_fires(self):
        called = []

        @define_component
        async def AsyncHookCmp(context):
            @on_before_destroy
            def hook():
                called.append("destroy")

            return html.DIV({}, "async")

        with TestRenderer.render(AsyncHookCmp) as result:
            result._instance._remove_element()
            assert "destroy" in called

    def test_async_body_framework_cleanup_runs_before_user_hook(self):
        order = []

        @define_component
        async def AsyncHookCmp(context):
            signal = Signal(0)
            effect(lambda: signal.value, on_cleanup=lambda: order.append("effect"))

            @on_before_destroy
            def hook():
                order.append("user")

            return html.DIV({}, str(signal.value))

        with TestRenderer.render(AsyncHookCmp) as result:
            result._instance._remove_element()
            assert order == ["effect", "user"]


class TestAsyncComponentAsyncResults:
    def test_async_body_use_async_result_collected(self):
        @define_component
        async def AsyncResultCmp(context):
            use_async_result(lambda: asyncio.sleep(0), immediate=False)
            return html.DIV({}, "async")

        with TestRenderer.render(AsyncResultCmp) as result:
            assert len(result._instance._async_results) == 1


class TestSyncComponentBehaviorUnchanged:
    def test_sync_component_hooks_extracted_at_setup(self):
        called = []

        @define_component
        def SyncHookCmp(context):
            @on_before_rendering
            def hook():
                called.append("before")

            return html.DIV({}, "sync")

        with TestRenderer.render(SyncHookCmp):
            assert "before" in called

    def test_sync_component_no_pending_async_template(self):
        @define_component
        def SyncCmp(context):
            return html.DIV({}, "sync")

        with TestRenderer.render(SyncCmp) as result:
            assert result._instance._pending_async_template is None


class TestSuspenseAsyncContext:
    def test_async_component_under_suspense_has_context(self):
        captured = []

        @define_component
        async def AsyncSuspenseChild(context):
            captured.append(_active_component_context.get())
            return html.DIV({}, "child")

        @define_component
        def SuspenseWrapper(context):
            return html.DIV(
                {},
                suspense(
                    fallback=lambda: html.P({}, "loading"),
                    children=lambda: AsyncSuspenseChild(None),
                ),
            )

        with TestRenderer.render(SuspenseWrapper):
            assert len(captured) == 1
            assert captured[0] is not None
            assert captured[0]._component_name == "AsyncSuspenseChild"

    def test_parallel_suspense_no_context_cross_contamination(self):
        captured = {}

        @define_component
        async def ChildA(context):
            await asyncio.sleep(0)
            captured["A"] = context._component_name
            return html.DIV({}, "A")

        @define_component
        async def ChildB(context):
            await asyncio.sleep(0)
            captured["B"] = context._component_name
            return html.DIV({}, "B")

        @define_component
        def SuspenseWrapper(context):
            return html.DIV(
                {},
                suspense(
                    fallback=lambda: html.P({}, "loading"),
                    children=lambda: html.DIV({}, ChildA(None), ChildB(None)),
                ),
            )

        with TestRenderer.render(SuspenseWrapper):
            assert captured.get("A") == "ChildA"
            assert captured.get("B") == "ChildB"

    def test_suspense_async_body_on_before_rendering_hook_fires(self):
        called = []

        @define_component
        async def AsyncSuspenseChild(context):
            await asyncio.sleep(0)

            @on_before_rendering
            def hook():
                called.append("before")

            return html.DIV({}, "child")

        @define_component
        def SuspenseWrapper(context):
            return html.DIV(
                {},
                suspense(
                    fallback=lambda: html.P({}, "loading"),
                    children=lambda: AsyncSuspenseChild(None),
                ),
            )

        with TestRenderer.render(SuspenseWrapper):
            assert "before" in called

    def test_suspense_async_body_on_after_rendering_hook_fires(self):
        called = []

        @define_component
        async def AsyncSuspenseChild(context):
            await asyncio.sleep(0)

            @on_after_rendering
            def hook():
                called.append("after")

            return html.DIV({}, "child")

        @define_component
        def SuspenseWrapper(context):
            return html.DIV(
                {},
                suspense(
                    fallback=lambda: html.P({}, "loading"),
                    children=lambda: AsyncSuspenseChild(None),
                ),
            )

        with TestRenderer.render(SuspenseWrapper):
            assert "after" in called

    def test_suspense_async_body_on_before_destroy_hook_fires(self):
        called = []
        child_holder = []

        @define_component
        async def AsyncSuspenseChild(context):
            await asyncio.sleep(0)

            @on_before_destroy
            def hook():
                called.append("destroy")

            return html.DIV({}, "child")

        @define_component
        def SuspenseWrapper(context):
            child = AsyncSuspenseChild(None)
            child_holder.append(child)
            return html.DIV(
                {},
                suspense(
                    fallback=lambda: html.P({}, "loading"),
                    children=lambda: child,
                ),
            )

        with TestRenderer.render(SuspenseWrapper):
            child_holder[0]._remove_element()
            assert "destroy" in called

    def test_suspense_async_body_use_async_result_collected(self):
        child_holder = []

        @define_component
        async def AsyncResultChild(context):
            await asyncio.sleep(0)
            use_async_result(lambda: asyncio.sleep(0), immediate=False)
            return html.DIV({}, "child")

        @define_component
        def SuspenseWrapper(context):
            child = AsyncResultChild(None)
            child_holder.append(child)
            return html.DIV(
                {},
                suspense(
                    fallback=lambda: html.P({}, "loading"),
                    children=lambda: child,
                ),
            )

        with TestRenderer.render(SuspenseWrapper):
            assert len(child_holder[0]._async_results) == 1

    def test_suspense_async_result_included_in_transfer_payload(self):
        from webcompy.aio._async_result import AsyncState
        from webcompy.hydration._collect import collect_transfer_data

        child_holder = []

        @define_component
        async def AsyncResultChild(context):
            await asyncio.sleep(0)
            use_async_result(lambda: asyncio.sleep(0), immediate=False)
            return html.DIV({}, "child")

        @define_component
        def SuspenseWrapper(context):
            child = AsyncResultChild(None)
            child_holder.append(child)
            return html.DIV(
                {},
                suspense(
                    fallback=lambda: html.P({}, "loading"),
                    children=lambda: child,
                ),
            )

        with TestRenderer.render(SuspenseWrapper):
            child = child_holder[0]
            assert len(child._async_results) == 1
            child._async_results[0]._state.value = AsyncState.SUCCESS
            child._async_results[0]._data.value = "transfer-data"

            class _FakeRoot:
                def __init__(self):
                    self._children = [child]

            payload = collect_transfer_data(_FakeRoot())
            component_id = child._property.get("component_id", "")
            assert component_id in payload.async_results
            assert payload.async_results[component_id].state == "success"
            assert payload.async_results[component_id].data == "transfer-data"


class TestAsyncComponentEffectCleanup:
    def test_effect_created_in_async_body_tracked_by_scope(self):
        cleaned = []

        @define_component
        async def AsyncEffectCmp(context):
            signal = Signal(0)
            effect(lambda: signal.value, on_cleanup=lambda: cleaned.append("clean"))
            return html.DIV({}, str(signal.value))

        with TestRenderer.render(AsyncEffectCmp) as result:
            assert len(result._instance._render_state.effect_scope._effects) == 1
            result._instance._remove_element()
            assert "clean" in cleaned


class TestAsyncComponentSetupFailureCleanup:
    def _drive_failure(self, component):
        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore, _register_deferred_components
        from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.ports._keys import HOST_PORT_KEY
        from webcompy_testing import FakeBrowserHostPort
        from webcompy_testing._utils import run_sync

        host = FakeBrowserHostPort()
        scope = DIScope()
        scope.provide(HOST_PORT_KEY, host)
        scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())
        scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
        token = _active_di_scope.set(scope)
        _register_deferred_components()
        try:
            instance = component(None)

            class _RealParent:
                def __init__(self) -> None:
                    self._children = [instance]

            instance._parent = _RealParent()
            instance._node_idx = 0
            with pytest.raises(RuntimeError, match="boom"):
                run_sync(instance._render())
        finally:
            _active_di_scope.reset(token)
        return host, instance

    def _drive_cancellation(self, component):
        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore, _register_deferred_components
        from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.ports._keys import HOST_PORT_KEY
        from webcompy_testing import FakeBrowserHostPort

        host = FakeBrowserHostPort()
        scope = DIScope()
        scope.provide(HOST_PORT_KEY, host)
        scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())
        scope.provide(_COMPONENT_STORE_KEY, ComponentStore())
        token = _active_di_scope.set(scope)
        _register_deferred_components()

        async def _run():
            instance = component(None)

            class _RealParent:
                def __init__(self) -> None:
                    self._children = [instance]

            instance._parent = _RealParent()
            instance._node_idx = 0
            task = asyncio.ensure_future(instance._render())
            while not host._window_listeners.get("resize"):
                await asyncio.sleep(0)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            return instance, host

        try:
            return asyncio.run(_run())
        finally:
            _active_di_scope.reset(token)

    def test_failed_async_setup_removes_event_listener(self):
        from webcompy import use_window_event

        @define_component
        async def FailingAsyncCmp(context):
            await asyncio.sleep(0)
            use_window_event("resize", 0)
            raise RuntimeError("boom")

        host, _ = self._drive_failure(FailingAsyncCmp)

        assert host._window_listeners.get("resize") == []

    def test_failed_async_setup_chains_prior_destroy_hook(self):
        from webcompy import use_window_event

        order: list[str] = []

        @define_component
        async def FailingAsyncCmp(context):
            await asyncio.sleep(0)

            @on_before_destroy
            def _user_hook():
                order.append("user")

            use_window_event("resize", 0)
            raise RuntimeError("boom")

        host, _ = self._drive_failure(FailingAsyncCmp)

        assert order == ["user"]
        assert host._window_listeners.get("resize") == []

    def test_failed_async_setup_destroy_hook_fires_only_once(self):
        order: list[str] = []

        @define_component
        async def FailingAsyncCmp(context):
            await asyncio.sleep(0)

            @on_before_destroy
            def _user_hook():
                order.append("user")

            raise RuntimeError("boom")

        _, instance = self._drive_failure(FailingAsyncCmp)

        assert order == ["user"]
        instance._detach_from_node()
        instance._detach_from_node()
        assert order == ["user"]

    def test_cancelled_async_setup_runs_destroy_hooks(self):
        from webcompy import use_window_event

        order: list[str] = []

        @define_component
        async def CancelledAsyncCmp(context):
            await asyncio.sleep(0)

            @on_before_destroy
            def _user_hook():
                order.append("user")

            use_window_event("resize", 0)
            await asyncio.sleep(1)

        instance, host = self._drive_cancellation(CancelledAsyncCmp)

        assert order == ["user"]
        assert host._window_listeners.get("resize") == []
        assert instance._parent._children == []

    def test_successful_async_setup_ordering_unchanged(self):
        from webcompy import use_window_event
        from webcompy.ports._keys import HOST_PORT_KEY

        order: list[str] = []

        @define_component
        async def AsyncOkCmp(context):
            await asyncio.sleep(0)
            effect(lambda: None, on_cleanup=lambda: order.append("effect"))

            @on_before_destroy
            def _user_hook():
                order.append("user")

            use_window_event("resize", 0)
            return html.DIV({}, "ok")

        with TestRenderer.render(AsyncOkCmp) as result:
            host = result._scope.inject(HOST_PORT_KEY)
            assert len(host._window_listeners.get("resize", [])) == 1
            result._instance._remove_element()
            assert order == ["effect", "user"]
            assert host._window_listeners.get("resize") == []
