import asyncio
import warnings

from webcompy.aio._async_result import AsyncState
from webcompy.components._hooks import (
    _active_component_context,
    on_after_rendering,
    on_before_destroy,
    on_before_rendering,
    use_async,
    use_async_result,
)
from webcompy.components._libs import Context
from webcompy.di._keys import HYDRATION_DATA_KEY
from webcompy.di._scope import DIScope
from webcompy.signal import Signal


class TestStandaloneLifecycleHooks:
    def test_on_before_rendering_registers_on_context(self):
        registered = []

        def setup_fn(ctx):
            @on_before_rendering
            def hook():
                registered.append("before_render")

        ctx = Context(
            props=None,
            slots={},
            component_name="TestComponent",
            title_getter=lambda: "",
            meta_getter=lambda: {},
            title_setter=lambda x: None,
            meta_setter=lambda k, v: None,
        )
        token = _active_component_context.set(ctx)
        try:
            setup_fn(ctx)
        finally:
            _active_component_context.reset(token)

        hooks = ctx.__get_lifecyclehooks__()
        assert "on_before_rendering" in hooks
        hooks["on_before_rendering"]()
        assert registered == ["before_render"]

    def test_on_after_rendering_registers_on_context(self):
        registered = []

        def setup_fn(ctx):
            @on_after_rendering
            def hook():
                registered.append("after_render")

        ctx = Context(
            props=None,
            slots={},
            component_name="TestComponent",
            title_getter=lambda: "",
            meta_getter=lambda: {},
            title_setter=lambda x: None,
            meta_setter=lambda k, v: None,
        )
        token = _active_component_context.set(ctx)
        try:
            setup_fn(ctx)
        finally:
            _active_component_context.reset(token)

        hooks = ctx.__get_lifecyclehooks__()
        assert "on_after_rendering" in hooks
        hooks["on_after_rendering"]()
        assert registered == ["after_render"]

    def test_on_before_destroy_registers_on_context(self):
        registered = []

        def setup_fn(ctx):
            @on_before_destroy
            def hook():
                registered.append("destroy")

        ctx = Context(
            props=None,
            slots={},
            component_name="TestComponent",
            title_getter=lambda: "",
            meta_getter=lambda: {},
            title_setter=lambda x: None,
            meta_setter=lambda k, v: None,
        )
        token = _active_component_context.set(ctx)
        try:
            setup_fn(ctx)
        finally:
            _active_component_context.reset(token)

        hooks = ctx.__get_lifecyclehooks__()
        assert "on_before_destroy" in hooks
        hooks["on_before_destroy"]()
        assert registered == ["destroy"]

    def test_hook_outside_context_raises_lookup_error(self):
        try:

            @on_after_rendering
            def bad():
                pass

            raise AssertionError("Should have raised LookupError")
        except LookupError:
            pass

    def test_nested_context_restores_parent(self):
        parent_registered = []

        def parent_setup(ctx):
            @on_after_rendering
            def parent_hook():
                parent_registered.append("parent")

        def child_setup(ctx):
            @on_after_rendering
            def child_hook():
                pass

        parent_ctx = Context(
            props=None,
            slots={},
            component_name="Parent",
            title_getter=lambda: "",
            meta_getter=lambda: {},
            title_setter=lambda x: None,
            meta_setter=lambda k, v: None,
        )
        child_ctx = Context(
            props=None,
            slots={},
            component_name="Child",
            title_getter=lambda: "",
            meta_getter=lambda: {},
            title_setter=lambda x: None,
            meta_setter=lambda k, v: None,
        )

        token_parent = _active_component_context.set(parent_ctx)
        try:
            parent_setup(parent_ctx)
            token_child = _active_component_context.set(child_ctx)
            try:
                child_setup(child_ctx)
            finally:
                _active_component_context.reset(token_child)
        finally:
            _active_component_context.reset(token_parent)

        parent_hooks = parent_ctx.__get_lifecyclehooks__()
        child_hooks = child_ctx.__get_lifecyclehooks__()
        assert "on_after_rendering" in parent_hooks
        assert "on_after_rendering" in child_hooks
        parent_hooks["on_after_rendering"]()
        assert parent_registered == ["parent"]

    def test_decorator_returns_original_function(self):
        def my_func():
            return 42

        ctx = Context(
            props=None,
            slots={},
            component_name="TestComponent",
            title_getter=lambda: "",
            meta_getter=lambda: {},
            title_setter=lambda x: None,
            meta_setter=lambda k, v: None,
        )
        token = _active_component_context.set(ctx)
        try:
            result = on_after_rendering(my_func)
        finally:
            _active_component_context.reset(token)

        assert result is my_func
        assert result() == 42


def _make_context():
    return Context(
        props=None,
        slots={},
        component_name="TestComponent",
        title_getter=lambda: "",
        meta_getter=lambda: {},
        title_setter=lambda x: None,
        meta_setter=lambda k, v: None,
    )


def _with_context(fn):
    ctx = _make_context()
    token = _active_component_context.set(ctx)
    try:
        result = fn(ctx)
    finally:
        _active_component_context.reset(token)
    return result, ctx


def _with_context_in_scope(fn, scope):
    import webcompy.di._scope as di_scope_module

    ctx = _make_context()
    component_token = _active_component_context.set(ctx)
    scope_token = di_scope_module._active_di_scope.set(scope)
    try:
        result = fn(ctx)
    finally:
        di_scope_module._active_di_scope.reset(scope_token)
        _active_component_context.reset(component_token)
    return result, ctx


class TestUseAsyncResult:
    def test_immediate_true_registers_on_after_rendering(self):
        def setup(ctx):
            return use_async_result(
                lambda: asyncio.sleep(0),
                immediate=True,
            )

        _result, ctx = _with_context(setup)
        hooks = ctx.__get_lifecyclehooks__()
        assert "on_after_rendering" in hooks

    def test_immediate_false_does_not_register(self):
        def setup(ctx):
            return use_async_result(
                lambda: asyncio.sleep(0),
                immediate=False,
            )

        _result, ctx = _with_context(setup)
        hooks = ctx.__get_lifecyclehooks__()
        assert "on_after_rendering" not in hooks

    def test_watch_registers_callback(self):
        query = Signal("a")
        refetched = []

        async def fetch():
            refetched.append(query.value)
            return query.value

        def setup(ctx):
            return use_async_result(
                fetch,
                watch=[query],
                immediate=False,
            )

        _result, _ctx = _with_context(setup)
        query.value = "b"
        assert len(refetched) >= 1
        assert refetched[-1] == "b"

    def test_on_before_destroy_cleans_up_watch(self):
        query = Signal("a")

        def setup(ctx):
            return use_async_result(
                lambda: asyncio.sleep(0),
                watch=[query],
                immediate=False,
            )

        result, ctx = _with_context(setup)
        hooks = ctx.__get_lifecyclehooks__()
        assert "on_before_destroy" in hooks

        hooks["on_before_destroy"]()
        refetched = []
        result.refetch = lambda *_: refetched.append(True)
        query.value = "c"
        assert len(refetched) == 0

    def test_refetch_executes_async_function(self):
        async def fetch():
            return 42

        def setup(ctx):
            return use_async_result(fetch, default=0)

        result, ctx = _with_context(setup)
        hooks = ctx.__get_lifecyclehooks__()
        hooks["on_after_rendering"]()
        assert result.data.value == 42
        assert result.state.value == AsyncState.SUCCESS

    def test_use_async_result_does_not_emit_userwarning(self):
        async def fetch():
            return "result"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            def setup(ctx):
                return use_async_result(fetch, default=0)

            result, _ = _with_context(setup)
        userwarnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(userwarnings) == 0
        assert result.data.value == 0

    def test_transfer_false_marks_result_non_transferable(self):
        async def fetch():
            return "data"

        def setup(ctx):
            return use_async_result(fetch, transfer=False)

        result, _ = _with_context(setup)
        assert result._transferable is False

    def test_transfer_default_keeps_result_transferable(self):
        async def fetch():
            return "data"

        def setup(ctx):
            return use_async_result(fetch)

        result, _ = _with_context(setup)
        assert result._transferable is True

    def test_missing_transfer_entry_falls_back_to_client_execution(self):
        async def fetch():
            return 42

        scope = DIScope()
        scope.provide(HYDRATION_DATA_KEY, {})

        def setup(ctx):
            return use_async_result(fetch, default=0, transfer=False)

        result, ctx = _with_context_in_scope(setup, scope)
        hooks = ctx.__get_lifecyclehooks__()
        assert "on_after_rendering" in hooks
        assert result._transferable is False


class TestUseAsync:
    def test_registers_on_after_rendering(self):
        called = []

        async def my_func():
            called.append(True)

        def setup(ctx):
            use_async(my_func)

        _, ctx = _with_context(setup)
        hooks = ctx.__get_lifecyclehooks__()
        assert "on_after_rendering" in hooks

    def test_async_function_called_on_hook_fire(self):
        called = []

        async def my_func():
            called.append(True)

        def setup(ctx):
            use_async(my_func)

        _, ctx = _with_context(setup)
        hooks = ctx.__get_lifecyclehooks__()
        hooks["on_after_rendering"]()
        assert len(called) == 1
