from __future__ import annotations

import pytest

from webcompy.reactive import Reactive, effect
from webcompy.reactive._composable import use_counter
from webcompy.reactive._effect import (
    effect_scope,
)
from webcompy.reactive._graph import reset_graph_state


@pytest.fixture(autouse=True)
def reset_state():
    reset_graph_state()
    yield
    reset_graph_state()


class TestEffectBasic:
    def test_effect_executes_immediately(self):
        results = []
        a = Reactive(1)
        effect(lambda: results.append(a.value))
        assert len(results) == 1
        assert results[0] == 1

    def test_effect_re_executes_on_dependency_change(self):
        results = []
        a = Reactive(1)
        effect(lambda: results.append(a.value))
        assert results == [1]
        a.value = 2
        assert results[-1] == 2

    def test_effect_tracks_multiple_dependencies(self):
        results = []
        a = Reactive(1)
        b = Reactive(2)
        effect(lambda: results.append(a.value + b.value))
        assert results == [3]
        a.value = 10
        assert results[-1] == 12
        b.value = 20
        assert results[-1] == 30

    def test_effect_dynamic_dependencies(self):
        results = []
        flag = Reactive(True)
        a = Reactive("A")
        b = Reactive("B")
        effect(lambda: results.append(a.value if flag.value else b.value))
        assert results == ["A"]
        flag.value = False
        assert results[-1] == "B"
        a.value = "A2"
        assert results[-1] == "B"
        b.value = "B2"
        assert results[-1] == "B2"


class TestEffectDispose:
    def test_effect_dispose_stops_execution(self):
        results = []
        a = Reactive(1)
        handle = effect(lambda: results.append(a.value))
        assert results == [1]
        handle.dispose()
        a.value = 2
        assert results == [1]

    def test_effect_cleanup_on_re_execution(self):
        cleanups = []
        a = Reactive(1)

        def effect_fn():
            val = a.value
            cleanups.append(f"setup-{val}")
            return lambda: cleanups.append(f"cleanup-{val}")

        _ = effect(effect_fn)
        assert "setup-1" in cleanups
        a.value = 2
        assert "cleanup-1" in cleanups
        assert "setup-2" in cleanups


class TestEffectOnCleanup:
    def test_on_cleanup_callback(self):
        cleanups = []
        a = Reactive(1)
        effect(lambda: a.value, on_cleanup=lambda: cleanups.append("cleaned"))
        a.value = 2
        assert len(cleanups) == 1
        assert cleanups == ["cleaned"]

    def test_on_cleanup_on_dispose(self):
        cleanups = []
        a = Reactive(1)
        handle = effect(lambda: a.value, on_cleanup=lambda: cleanups.append("cleaned"))
        handle.dispose()
        assert "cleaned" in cleanups


class TestEffectScope:
    def test_scope_dispose_cleans_up_effects(self):
        results = []
        a = Reactive(1)

        with effect_scope() as scope:
            effect(lambda: results.append(a.value))

        assert results == [1]
        scope.dispose()
        a.value = 2
        assert results == [1]

    def test_nested_scopes(self):
        results = []
        a = Reactive(1)

        with effect_scope() as outer:
            effect(lambda: results.append(f"outer-{a.value}"))

            with effect_scope() as _inner:
                effect(lambda: results.append(f"inner-{a.value}"))

            a.value = 2

        outer.dispose()
        a.value = 3
        assert "outer-1" in results
        assert "inner-1" in results


class TestComposable:
    def test_use_counter_basic(self):
        count, increment, decrement = use_counter(0)
        assert count.value == 0
        increment()
        assert count.value == 1
        decrement()
        assert count.value == 0

    def test_use_counter_auto_cleanup_on_scope_disposal(self):
        count, increment, _decrement = use_counter(0)
        results = []

        with effect_scope() as scope:
            effect(lambda: results.append(count.value))

        assert results == [0]
        scope.dispose()
        increment()
        assert results == [0]
