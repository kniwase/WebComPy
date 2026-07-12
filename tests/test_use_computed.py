"""Tests for use_computed() composable."""

import warnings

import pytest

from webcompy.components._context_manager import ComponentRenderState, component_context
from webcompy.signal import Computed, Signal, use_computed
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


class TestUseComputedImports:
    def test_import_from_webcompy_top_level(self):
        from webcompy import use_computed as top_level_use_computed

        assert callable(top_level_use_computed)

    def test_import_from_webcompy_signal(self):
        from webcompy.signal import use_computed as signal_use_computed

        assert callable(signal_use_computed)

    def test_old_computed_is_removed(self):
        with pytest.raises(ImportError):
            from webcompy.signal import computed  # type: ignore[import-not-found]  # noqa: F401


class TestUseComputedFactory:
    def test_returns_computed(self):
        count = Signal(5)
        doubled = use_computed(lambda: count.value * 2)
        assert isinstance(doubled, Computed)
        assert doubled.value == 10

    def test_dependency_tracking(self):
        count = Signal(1)
        doubled = use_computed(lambda: count.value * 2)
        assert doubled.value == 2
        count.value = 7
        assert doubled.value == 14


class TestUseComputedBehavior:
    def test_no_warning_outside_component_context(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            doubled = use_computed(lambda: 2)
        assert doubled.value == 2
        assert not any(issubclass(x.category, UserWarning) for x in w)

    def test_not_registered_for_transfer(self):
        state = make_state()
        count = Signal(1)
        with component_context(state):
            doubled = use_computed(lambda: count.value * 2)
        assert doubled.value == 2
        assert len(state.context._transferable_signals) == 0

    def test_non_callable_first_arg_raises_type_error(self):
        with pytest.raises(TypeError, match="use_computed"):
            use_computed(0)  # type: ignore[arg-type]


class TestUseComputedTypeAnnotation:
    def test_type_annotation_works(self):
        count = Signal(5)
        doubled: Computed[int] = use_computed(lambda: count.value * 2)
        assert isinstance(doubled, Computed)
        assert doubled.value == 10
