from __future__ import annotations

from contextlib import contextmanager

import pytest

from tests.conftest import FakeDOMNode
from webcompy.elements.types._dynamic import _subtree_has_async_setup
from webcompy.elements.types._element import Element


async def _dummy_async_template():
    from webcompy.elements import html

    return html.DIV({}, "resolved")


def _make_pending_coro():
    return _dummy_async_template()


class FakeParent(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


@contextmanager
def _component_di_scope():
    from webcompy.components._component import HeadPropsStore
    from webcompy.components._generator import ComponentStore
    from webcompy.di import _pending_di_parent
    from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
    from webcompy.di._scope import DIScope, _active_di_scope

    store = ComponentStore()
    head_props = HeadPropsStore()
    parent_scope = _active_di_scope.get(None)
    scope = parent_scope.create_child() if parent_scope is not None else DIScope()
    scope.provide(_COMPONENT_STORE_KEY, store)
    scope.provide(_HEAD_PROPS_KEY, head_props)
    di_token = _active_di_scope.set(scope)
    pending_token = _pending_di_parent.set(scope)
    try:
        yield scope, store, head_props
    finally:
        _active_di_scope.reset(di_token)
        _pending_di_parent.reset(pending_token)
        scope.dispose()


class TestSubtreeHasAsyncSetup:
    def test_plain_element_returns_false(self):
        el = Element("div", {}, {}, None, None)
        assert _subtree_has_async_setup(el) is False

    def test_element_with_empty_children_returns_false(self):
        parent = Element("div", {}, {}, None, ["hello"])
        assert _subtree_has_async_setup(parent) is False

    def test_component_without_pending_returns_false(self, fake_browser_full):
        from webcompy.components._generator import define_component
        from webcompy.elements import html

        @define_component
        def SyncCmp(context):
            return html.DIV({}, "sync")

        with _component_di_scope():
            cmp = SyncCmp(None)
            assert _subtree_has_async_setup(cmp) is False

    def test_component_with_pending_returns_true(self, fake_browser_full):
        from webcompy.components._generator import define_component
        from webcompy.elements import html

        @define_component
        def SyncCmp(context):
            return html.DIV({}, "sync")

        with _component_di_scope():
            cmp = SyncCmp(None)
            cmp._pending_async_template = _make_pending_coro()
            assert _subtree_has_async_setup(cmp) is True

    def test_children_containing_async_component_returns_true(self, fake_browser_full):
        from webcompy.components._generator import define_component
        from webcompy.elements import html

        @define_component
        def SyncCmp(context):
            return html.DIV({}, "sync")

        with _component_di_scope():
            cmp = SyncCmp(None)
            cmp._pending_async_template = _make_pending_coro()
            parent = Element("div", {}, {}, None, None)
            parent._children = [cmp]
            assert _subtree_has_async_setup(parent) is True

    def test_deep_nested_async_component_returns_true(self, fake_browser_full):
        from webcompy.components._generator import define_component
        from webcompy.elements import html

        @define_component
        def SyncCmp(context):
            return html.DIV({}, "sync")

        with _component_di_scope():
            cmp = SyncCmp(None)
            cmp._pending_async_template = _make_pending_coro()
            inner = Element("div", {}, {}, None, None)
            inner._children = [cmp]
            outer = Element("div", {}, {}, None, None)
            outer._children = [inner]
            assert _subtree_has_async_setup(outer) is True

    def test_sync_component_wrapping_async_child_returns_true(self, fake_browser_full):
        from webcompy.components._generator import define_component
        from webcompy.elements import html

        @define_component
        def AsyncCmp(context):
            return html.DIV({}, "async")

        @define_component
        def SyncWrapper(context):
            return html.DIV({}, "sync")

        with _component_di_scope():
            async_cmp = AsyncCmp(None)
            async_cmp._pending_async_template = _make_pending_coro()
            wrapper = _make_sync_component_with_children([async_cmp])
            assert _subtree_has_async_setup(wrapper) is True


def _make_sync_component_with_children(children):
    from webcompy.components._component import Component

    cmp = object.__new__(Component)
    cmp._children = children
    cmp._pending_async_template = None
    cmp._callback_nodes = []
    return cmp


class TestRepeatElementAsyncRefreshRegistration:
    @pytest.mark.asyncio
    async def test_repeat_registers_async_refresh_when_async_subtree(self, fake_browser_full, monkeypatch):
        from webcompy.components._generator import define_component
        from webcompy.elements import html
        from webcompy.elements.types._repeat import RepeatElement
        from webcompy.signal import ReactiveList

        @define_component
        def MyCmp(context):
            return html.DIV({}, context.props)

        with _component_di_scope():
            rl = ReactiveList(["a"])

            def template(x):
                cmp = MyCmp(x)
                cmp._pending_async_template = _make_pending_coro()
                return cmp

            rep = RepeatElement(rl, template)
            root_fake = FakeDOMNode("div")
            parent = FakeParent("div", {}, {}, None, None)
            parent._node_cache = root_fake
            parent._mounted = True
            rep._parent = parent
            rep._node_idx = 0

            refresh_sync_called = []
            original_refresh_sync = rep._refresh_sync

            def tracking_refresh_sync(*args, **kwargs):
                refresh_sync_called.append(True)
                return original_refresh_sync(*args, **kwargs)

            monkeypatch.setattr(rep, "_refresh_sync", tracking_refresh_sync)

            await rep._render()

            rl.append("b")
            import asyncio

            await asyncio.sleep(0)

            assert len(refresh_sync_called) == 0, "_refresh_sync should NOT be called when subtree has async setup"

    @pytest.mark.asyncio
    async def test_repeat_registers_sync_refresh_when_sync_subtree(self, fake_browser_full, monkeypatch):
        from webcompy.components._generator import define_component
        from webcompy.elements import html
        from webcompy.elements.types._repeat import RepeatElement
        from webcompy.signal import ReactiveList

        @define_component
        def MyCmp(context):
            return html.DIV({}, context.props)

        with _component_di_scope():
            rl = ReactiveList(["a"])
            rep = RepeatElement(rl, lambda x: MyCmp(x))
            root_fake = FakeDOMNode("div")
            parent = FakeParent("div", {}, {}, None, None)
            parent._node_cache = root_fake
            parent._mounted = True
            rep._parent = parent
            rep._node_idx = 0

            refresh_sync_called = []
            original_refresh_sync = rep._refresh_sync

            def tracking_refresh_sync(*args, **kwargs):
                refresh_sync_called.append(True)
                return original_refresh_sync(*args, **kwargs)

            monkeypatch.setattr(rep, "_refresh_sync", tracking_refresh_sync)

            await rep._render()

            rl.append("b")
            import asyncio

            await asyncio.sleep(0)

            assert len(refresh_sync_called) > 0, "_refresh_sync SHOULD be called when subtree has no async setup"


class TestSwitchElementAsyncRefreshRegistration:
    @pytest.mark.asyncio
    async def test_switch_registers_async_refresh_when_async_subtree(self, fake_browser_full, monkeypatch):
        from webcompy.components._generator import define_component
        from webcompy.elements import html
        from webcompy.elements.types._switch import SwitchElement
        from webcompy.signal import Signal

        @define_component
        def MyCmp(context):
            return html.DIV({}, context.props)

        with _component_di_scope():
            cond = Signal(True)

            def cmp_generator():
                cmp = MyCmp("test")
                cmp._pending_async_template = _make_pending_coro()
                return cmp

            sw = SwitchElement([(cond, cmp_generator)], None)
            root_fake = FakeDOMNode("div")
            parent = FakeParent("div", {}, {}, None, None)
            parent._node_cache = root_fake
            parent._mounted = True
            sw._parent = parent
            sw._node_idx = 0

            refresh_sync_called = []
            original_refresh_sync = sw._refresh_sync

            def tracking_refresh_sync(*args, **kwargs):
                refresh_sync_called.append(True)
                return original_refresh_sync(*args, **kwargs)

            monkeypatch.setattr(sw, "_refresh_sync", tracking_refresh_sync)

            await sw._render()

            cond.value = False
            import asyncio

            await asyncio.sleep(0)

            assert len(refresh_sync_called) == 0, "_refresh_sync should NOT be called when subtree has async setup"


class TestFoundationValidationSpike:
    @pytest.mark.asyncio
    async def test_async_component_in_repeat_signal_update_does_not_block(self, fake_browser_full, monkeypatch):
        from webcompy.components._generator import define_component
        from webcompy.elements import html
        from webcompy.elements.types._repeat import RepeatElement
        from webcompy.signal import ReactiveList

        @define_component
        async def DataComponent(context):
            data = "Alice"
            return html.DIV({}, str(data))

        with _component_di_scope():
            rl = ReactiveList(["item1"])

            rep = RepeatElement(rl, lambda x: DataComponent(x))
            root_fake = FakeDOMNode("div")
            parent = FakeParent("div", {}, {}, None, None)
            parent._node_cache = root_fake
            parent._mounted = True
            rep._parent = parent
            rep._node_idx = 0

            refresh_sync_called = []
            original_refresh_sync = rep._refresh_sync

            def tracking_refresh_sync(*args, **kwargs):
                refresh_sync_called.append(True)
                return original_refresh_sync(*args, **kwargs)

            monkeypatch.setattr(rep, "_refresh_sync", tracking_refresh_sync)

            await rep._render()

            rl.append("item2")
            import asyncio

            await asyncio.sleep(0)

            assert len(refresh_sync_called) == 0, (
                "Signal-triggered RepeatElement._refresh() whose subtree contains "
                "an async component must NOT block the event loop"
            )

    @pytest.mark.asyncio
    async def test_async_setup_exception_propagates_not_swallowed(self, fake_browser_full):
        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore, define_component
        from webcompy.di import _pending_di_parent
        from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements import html

        @define_component
        async def FailingComponent(context):
            msg = "async-setup-failure"
            return html.DIV({}, msg)

        store = ComponentStore()
        head_props = HeadPropsStore()
        scope = DIScope()
        scope.provide(_COMPONENT_STORE_KEY, store)
        scope.provide(_HEAD_PROPS_KEY, head_props)
        di_token = _active_di_scope.set(scope)
        pending_token = _pending_di_parent.set(scope)
        try:
            cmp = FailingComponent(None)
            assert cmp._pending_async_template is not None

            parent = Element("div", {}, {}, None, None)
            parent._children = [cmp]
            cmp._parent = parent

            cmp._pending_async_template = _raise_value_error()
            with pytest.raises(ValueError, match="async-setup-error"):
                await cmp._render()

            assert cmp not in parent._children, "component should be removed from parent after failed async setup"
            assert cmp._pending_async_template is None, "_pending_async_template should be cleared on failure"
            assert len(cmp._callback_nodes) == 0, "callback nodes should be cleaned up on failure"
        finally:
            _active_di_scope.reset(di_token)
            _pending_di_parent.reset(pending_token)
            scope.dispose()

    @pytest.mark.asyncio
    async def test_async_setup_exception_cleans_up_signal_graph(self, fake_browser_full):
        from webcompy.components._component import HeadPropsStore
        from webcompy.components._generator import ComponentStore, define_component
        from webcompy.di import _pending_di_parent
        from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
        from webcompy.di._scope import DIScope, _active_di_scope
        from webcompy.elements import html

        @define_component
        async def FailingComponent(context):
            msg = "async-setup-failure"
            return html.DIV({}, msg)

        store = ComponentStore()
        head_props = HeadPropsStore()
        scope = DIScope()
        scope.provide(_COMPONENT_STORE_KEY, store)
        scope.provide(_HEAD_PROPS_KEY, head_props)
        di_token = _active_di_scope.set(scope)
        pending_token = _pending_di_parent.set(scope)
        try:
            cmp = FailingComponent(None)
            assert cmp._pending_async_template is not None

            cmp._pending_async_template = _raise_value_error()
            with pytest.raises(ValueError, match="async-setup-error"):
                await cmp._render()

            assert cmp._property["on_before_destroy"]() is None, "on_before_destroy should not raise after cleanup"
        finally:
            _active_di_scope.reset(di_token)
            _pending_di_parent.reset(pending_token)
            scope.dispose()


async def _raise_value_error():
    raise ValueError("async-setup-error")
