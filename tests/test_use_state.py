"""Tests for use_state(), use_reactive_list(), use_reactive_dict() composables."""

import warnings

import pytest

from webcompy.components._context_manager import ComponentRenderState, component_context
from webcompy.components._hooks import on_before_rendering
from webcompy.components._libs import Context, generate_id
from webcompy.di._keys import HYDRATION_SIGNAL_DATA_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.signal import (
    ReactiveDict,
    ReactiveList,
    Signal,
    use_reactive_dict,
    use_reactive_list,
    use_state,
)
from webcompy.signal._composable import _auto_key
from webcompy.signal._effect import EffectScope


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


class TestSignalConstructor:
    def test_constructor_emits_no_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            s = Signal(0)
        assert len(w) == 0
        assert s.value == 0

    def test_signal_type_annotation_works(self):
        state = make_state()
        with component_context(state):
            s: Signal[int] = use_state(lambda: 42)
        assert isinstance(s, Signal)
        assert s.value == 42


class TestReactiveListConstructor:
    def test_constructor_emits_no_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rl = ReactiveList([1, 2, 3])
        assert len(w) == 0
        assert rl.value == [1, 2, 3]

    def test_mutation_methods_work(self):
        rl = ReactiveList([1, 2])
        rl.append(3)
        assert rl.value == [1, 2, 3]
        popped = rl.pop()
        assert popped == 3
        assert rl.value == [1, 2]


class TestReactiveDictConstructor:
    def test_constructor_emits_no_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rd = ReactiveDict({"a": 1})
        assert len(w) == 0
        assert rd.value == {"a": 1}

    def test_mutation_methods_work(self):
        rd = ReactiveDict({"a": 1})
        rd["b"] = 2
        assert rd.value == {"a": 1, "b": 2}
        rd.pop("a")
        assert rd.value == {"b": 2}


class TestUseStateInsideComponent:
    def test_factory_runs_when_no_payload(self):
        state = make_state()
        with component_context(state):
            calls: list = []

            def factory() -> int:
                calls.append("called")
                return 7

            s = use_state(factory)
        assert s.value == 7
        assert calls == ["called"]

    def test_auto_key_registers_in_transferable(self):
        state = make_state()
        with component_context(state):
            s = use_state(lambda: 0)
        assert len(state.context._transferable_signals) == 1
        assert next(iter(state.context._transferable_signals.values())) is s

    def test_explicit_key(self):
        state = make_state()
        with component_context(state):
            s = use_state("counter", lambda: 99)
        assert "counter" in state.context._transferable_signals
        assert state.context._transferable_signals["counter"] is s

    def test_factory_skip_during_hydration(self):
        state = make_state()
        cid = generate_id("TestComp")
        payload = {cid: {"my_key": 12345}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        try:
            with component_context(state):
                calls: list = []

                def factory() -> int:
                    calls.append("called")
                    return 0

                s = use_state("my_key", factory)
            assert s.value == 12345
            assert calls == []
            assert state.context._transferable_signals["my_key"] is s
        finally:
            _active_di_scope.reset(token)

    def test_factory_runs_when_payload_missing_key(self):
        state = make_state()
        cid = generate_id("TestComp")
        payload = {cid: {}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        try:
            with component_context(state):
                s = use_state("missing_key", lambda: 42)
            assert s.value == 42
        finally:
            _active_di_scope.reset(token)

    def test_container_mutation_does_not_leak_into_payload(self):
        state = make_state()
        cid = generate_id("TestComp")
        payload = {cid: {"settings": {"theme": "dark"}}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        try:
            with component_context(state):
                s = use_state("settings", lambda: {})
            s.value["theme"] = "light"
            assert payload[cid]["settings"] == {"theme": "dark"}
            with component_context(make_state()):
                s2 = use_state("settings", lambda: {})
            assert s2.value == {"theme": "dark"}
        finally:
            _active_di_scope.reset(token)


class TestUseStateOutsideComponent:
    def test_factory_runs_and_warning_emitted(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            s = use_state(lambda: 5)
        assert s.value == 5
        assert any(issubclass(x.category, UserWarning) for x in w)
        assert any("outside component setup" in str(x.message) for x in w)

    def test_outside_context_returns_signal_instance(self):
        s = use_state(lambda: 0)
        assert isinstance(s, Signal)
        assert s.value == 0

    def test_non_callable_first_arg_raises_type_error(self):
        with pytest.raises(TypeError, match="use_state"):
            use_state(0)

    def test_str_without_factory_raises_type_error(self):
        with pytest.raises(TypeError, match="use_state"):
            use_state("key")  # type: ignore[call-overload]


class TestUseStateInLifecycleHook:
    def test_use_state_inside_on_before_rendering_warns(self):
        ctx = Context(
            props=None,
            slots={},
            component_name="TestComponent",
            title_getter=lambda: "",
            meta_getter=lambda: {},
            title_setter=lambda x: None,
            meta_setter=lambda k, v: None,
        )
        state = ComponentRenderState(
            context=ctx,
            effect_scope=EffectScope(),
            framework_cleanup=lambda: None,
        )
        hook_signals: list = []

        with component_context(state):

            @on_before_rendering
            def hook():
                s = use_state(lambda: 42)
                hook_signals.append(s)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            hooks = ctx.__get_lifecyclehooks__()
            hooks["on_before_rendering"]()

        assert len(hook_signals) == 1
        assert hook_signals[0].value == 42
        assert any(issubclass(x.category, UserWarning) and "outside component setup" in str(x.message) for x in w)
        assert len(ctx._transferable_signals) == 0


class TestUseReactiveList:
    def test_factory_runs_when_no_payload(self):
        state = make_state()
        with component_context(state):
            rl = use_reactive_list(lambda: [1, 2, 3])
        assert rl.value == [1, 2, 3]

    def test_factory_skip_during_hydration(self):
        state = make_state()
        cid = generate_id("TestComp")
        payload = {cid: {"items": [10, 20, 30]}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        try:
            with component_context(state):
                rl = use_reactive_list("items", lambda: [])
            assert rl.value == [10, 20, 30]
        finally:
            _active_di_scope.reset(token)

    def test_mutation_methods_work_on_restored(self):
        state = make_state()
        cid = generate_id("TestComp")
        payload = {cid: {"items": [1, 2]}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        try:
            with component_context(state):
                rl = use_reactive_list("items", lambda: [])
            rl.append(3)
            assert rl.value == [1, 2, 3]
            cb_results: list = []
            rl.on_after_updating(lambda v: cb_results.append(list(v)))
            rl.append(4)
            assert cb_results == [[1, 2, 3, 4]]
        finally:
            _active_di_scope.reset(token)

    def test_mutation_does_not_leak_into_payload(self):
        state = make_state()
        cid = generate_id("TestComp")
        payload = {cid: {"items": [1, 2]}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        try:
            with component_context(state):
                rl1 = use_reactive_list("items", lambda: [])
            rl1.append(3)
            assert payload[cid]["items"] == [1, 2]
            with component_context(make_state()):
                rl2 = use_reactive_list("items", lambda: [])
            assert rl2.value == [1, 2]
        finally:
            _active_di_scope.reset(token)

    def test_outside_component_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rl = use_reactive_list(lambda: [1])
        assert isinstance(rl, ReactiveList)
        assert any("outside component setup" in str(x.message) for x in w)


class TestUseReactiveDict:
    def test_factory_runs_when_no_payload(self):
        state = make_state()
        with component_context(state):
            rd = use_reactive_dict(lambda: {"a": 1})
        assert rd.value == {"a": 1}

    def test_factory_skip_during_hydration(self):
        state = make_state()
        cid = generate_id("TestComp")
        payload = {cid: {"settings": {"theme": "dark"}}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        try:
            with component_context(state):
                rd = use_reactive_dict("settings", lambda: {})
            assert rd.value == {"theme": "dark"}
        finally:
            _active_di_scope.reset(token)

    def test_mutation_methods_work_on_restored(self):
        state = make_state()
        cid = generate_id("TestComp")
        payload = {cid: {"s": {"a": 1}}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        try:
            with component_context(state):
                rd = use_reactive_dict("s", lambda: {})
            rd["b"] = 2
            assert rd.value == {"a": 1, "b": 2}
        finally:
            _active_di_scope.reset(token)

    def test_mutation_does_not_leak_into_payload(self):
        state = make_state()
        cid = generate_id("TestComp")
        payload = {cid: {"s": {"a": 1}}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        try:
            with component_context(state):
                rd1 = use_reactive_dict("s", lambda: {})
            rd1["b"] = 2
            assert payload[cid]["s"] == {"a": 1}
            with component_context(make_state()):
                rd2 = use_reactive_dict("s", lambda: {})
            assert rd2.value == {"a": 1}
        finally:
            _active_di_scope.reset(token)

    def test_outside_component_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rd = use_reactive_dict(lambda: {"k": 1})
        assert isinstance(rd, ReactiveDict)
        assert any("outside component setup" in str(x.message) for x in w)


class TestAutoKey:
    def test_returns_string_with_colon(self):
        from webcompy.signal._composable import AutoKey

        k = _auto_key()
        assert isinstance(k, AutoKey)
        assert ":" in str(k) or k.lineno > 0

    def test_two_calls_on_different_lines_produce_distinct_keys(self):
        k1 = _auto_key()
        k2 = _auto_key()
        assert k1 != k2

    def test_same_line_calls_get_distinct_keys(self):
        state = make_state()
        with component_context(state):
            _s1 = use_state(lambda: 1); _s2 = use_state(lambda: 2)  # fmt: skip  # noqa: E702
        keys = list(state.context._transferable_signals.keys())
        assert len(keys) == 2
        assert keys[0] != keys[1]
        assert state.context._transferable_signals[keys[0]].value == 1
        assert state.context._transferable_signals[keys[1]].value == 2

    def test_auto_key_is_module_based_not_filesystem_path(self):
        k = _auto_key()
        prefix = str(k).split(":", 1)[0]
        assert prefix == __name__, f"auto-key must be module-based for cross-environment transfer: {k!r}"
        assert not str(k).startswith("/"), f"auto-key must not embed the filesystem path: {k!r}"


class TestRoundTrip:
    def test_signal_ssr_collects_then_browser_restores(self):
        state = make_state()
        scope = DIScope()
        token = _active_di_scope.set(scope)
        try:
            with component_context(state):
                s = use_state("count", lambda: 5)
            assert s.value == 5
            assert state.context._transferable_signals["count"] is s

            cid = generate_id("TestComp")
            payload = {cid: {"count": 999}}
            scope2 = DIScope()
            scope2.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
            token2 = _active_di_scope.set(scope2)
            try:
                state2 = make_state()
                with component_context(state2):
                    s2 = use_state("count", lambda: 0)
                assert s2.value == 999
            finally:
                _active_di_scope.reset(token2)
        finally:
            _active_di_scope.reset(token)


class TestRestoredNoNotifications:
    def test_restored_value_does_not_trigger_callbacks(self):
        state = make_state()
        cid = generate_id("TestComp")
        payload = {cid: {"k": 100}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        try:
            with component_context(state):
                s = use_state("k", lambda: 0)
            results: list = []
            s.on_after_updating(lambda v: results.append(v))
            s.value = 200
            assert results == [200]
        finally:
            _active_di_scope.reset(token)


class TestRestoreAcceptsDifferentTypes:
    def test_restored_signal_holds_value_regardless_of_type(self):
        state = make_state()
        cid = generate_id("TestComp")
        payload = {cid: {"k": [1, 2, 3]}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        try:
            with component_context(state):
                s = use_state("k", lambda: 0)
            assert s.value == [1, 2, 3]
        finally:
            _active_di_scope.reset(token)


class TestInternalComposables:
    def test_head_props_store_does_not_emit_userwarning(self):
        from webcompy.components._component import HeadPropsStore

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            store = HeadPropsStore()
        userwarnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert not any("Direct Signal" in str(x.message) for x in userwarnings)
        assert not any("Direct ReactiveDict" in str(x.message) for x in userwarnings)
        assert store.titles.value == {}
        assert store.head_metas.value == {}

    def test_use_counter_does_not_emit_userwarning(self):
        from webcompy.signal._composable import use_counter

        state = make_state()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with component_context(state):
                count, inc, dec = use_counter(0)
                inc()
                dec()
        userwarnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert not any("Direct Signal" in str(x.message) for x in userwarnings)
        assert count.value == 0

    def test_use_async_result_does_not_emit_userwarning(self):
        from webcompy.aio._async_result import AsyncResult

        async def fetch():
            return "result"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            AsyncResult(fetch)
        userwarnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert not any("Direct Signal" in str(x.message) for x in userwarnings)

    def test_use_theme_does_not_emit_userwarning(self):
        from unittest.mock import MagicMock

        from webcompy.ui.theme._manager import ThemeManager
        from webcompy.ui.theme._theme import Theme

        app = MagicMock()
        render_ctx = MagicMock()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ThemeManager(app, render_ctx, Theme.LIGHT)
        userwarnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert not any("Direct Signal" in str(x.message) for x in userwarnings)
        assert not any("Computed" in str(x.message) for x in userwarnings)


class TestMultipleAutoKeys:
    def test_two_auto_keyed_calls_produce_distinct_keys(self):
        state = make_state()

        def setup(ctx):
            s1 = use_state(lambda: 1)
            s2 = use_state(lambda: 2)
            return s1, s2

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with component_context(state):
                setup(state.context)
        assert len(state.context._transferable_signals) == 2
        keys = list(state.context._transferable_signals.keys())
        assert keys[0] != keys[1]
        collision_warnings = [x for x in w if "collision" in str(x.message).lower()]
        assert len(collision_warnings) == 0

    def test_three_auto_keyed_calls_in_setup(self):
        state = make_state()

        def setup(ctx):
            a = use_state(lambda: "a")
            b = use_state(lambda: "b")
            c = use_state(lambda: "c")
            return a, b, c

        with component_context(state):
            setup(state.context)
        assert len(state.context._transferable_signals) == 3


class TestAutoKeyCollision:
    def test_same_explicit_key_emits_duplicate_warning(self):
        state = make_state()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with component_context(state):
                use_state("k", lambda: 1)
                use_state("k", lambda: 2)
        duplicate_warnings = [x for x in w if "duplicate" in str(x.message).lower()]
        assert len(duplicate_warnings) >= 1
        assert not any("collision" in str(x.message).lower() for x in duplicate_warnings)

    def test_same_line_auto_key_collision_with_fallback_emits_warning(self):
        from unittest.mock import patch

        from webcompy.signal._composable import AutoKey

        fake_key = AutoKey("same.py", 1, None)
        state = make_state()
        with (
            patch("webcompy.signal._composable._auto_key", return_value=fake_key),
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")
            with component_context(state):
                use_state(lambda: 1)
                use_state(lambda: 2)
        collision_warnings = [x for x in w if "collision" in str(x.message).lower()]
        assert len(collision_warnings) == 1
        assert state.context._transferable_signals["same.py:1"].value == 1

    def test_explicit_key_collision_message_does_not_mention_explicit_key_fix(self):
        state = make_state()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with component_context(state):
                use_state("k", lambda: 1)
                use_state("k", lambda: 2)
        msgs = [str(x.message).lower() for x in w if "duplicate" in str(x.message).lower()]
        assert any("explicit key" in m for m in msgs)
        assert not any("use an explicit key" in m for m in msgs)

    def test_auto_key_collision_message_mentions_explicit_key_fix(self):
        from unittest.mock import patch

        from webcompy.signal._composable import AutoKey

        fake_key = AutoKey("same.py", 1, None)
        state = make_state()
        with (
            patch("webcompy.signal._composable._auto_key", return_value=fake_key),
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")
            with component_context(state):
                use_state(lambda: 1)
                use_state(lambda: 2)
        msgs = [str(x.message).lower() for x in w if "collision" in str(x.message).lower()]
        assert any("use an explicit key" in m for m in msgs)


class TestValidateFactory:
    def test_keyword_only_required_param_warns(self):
        from webcompy.signal._composable import _validate_factory

        def factory(*, required):
            return required

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _validate_factory(factory)
        assert any("arguments" in str(x.message).lower() for x in w)

    def test_positional_only_required_param_warns(self):
        from webcompy.signal._composable import _validate_factory

        def factory(required, /):
            return required

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _validate_factory(factory)
        assert any("arguments" in str(x.message).lower() for x in w)

    def test_var_positional_does_not_warn(self):
        from webcompy.signal._composable import _validate_factory

        def factory(*args):
            return args

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _validate_factory(factory)
        factory_warnings = [x for x in w if "arguments" in str(x.message).lower()]
        assert len(factory_warnings) == 0


class TestCollectExcludesComputed:
    def test_collect_transfer_data_excludes_computed(self):
        from unittest.mock import MagicMock

        from webcompy.components._component import Component
        from webcompy.hydration._collect import _collect_component_signals
        from webcompy.signal import Signal
        from webcompy.signal._computed import Computed

        src = Signal(5)
        doubled = Computed(lambda: src.value * 2)

        component = MagicMock(spec=Component)
        component.__signal_members__ = {
            "src": src,
            "doubled": doubled,
            "not_a_signal": "raw",
        }
        component._property = {"component_id": "test-cid"}

        result = _collect_component_signals(component)
        assert "src" in result
        assert "doubled" not in result
        assert "not_a_signal" not in result
        assert result["src"] == 5
