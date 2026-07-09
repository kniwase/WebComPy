from __future__ import annotations

from typing import Any

import pytest

from webcompy.components._context_manager import ComponentRenderState, component_context
from webcompy.components._hooks import _active_component_context, _active_effect_scope
from webcompy.components._libs import Context
from webcompy.signal._effect import _active_scope, create_effect_scope


def _make_context(name: str = "TestComponent") -> Context[Any]:
    return Context(
        props=None,
        slots={},
        component_name=name,
        title_getter=lambda: "",
        meta_getter=lambda: {},
        title_setter=lambda x: None,
        meta_setter=lambda k, v: None,
    )


def _make_state(name: str = "TestComponent") -> ComponentRenderState:
    return ComponentRenderState(
        context=_make_context(name),
        effect_scope=create_effect_scope(),
        framework_cleanup=lambda: None,
    )


class TestComponentContext:
    def test_activates_context_and_scope(self):
        state = _make_state()
        assert _active_component_context.get(None) is None
        assert _active_effect_scope.get(None) is None
        assert _active_scope.get(None) is None

        with component_context(state):
            assert _active_component_context.get() is state.context
            assert _active_effect_scope.get() is state.effect_scope
            assert _active_scope.get() is state.effect_scope

    def test_resets_context_and_scope_on_exit(self):
        state = _make_state()
        with component_context(state):
            pass

        assert _active_component_context.get(None) is None
        assert _active_effect_scope.get(None) is None
        assert _active_scope.get(None) is None

    def test_resets_on_exception(self):
        state = _make_state()
        with pytest.raises(ValueError, match="boom"), component_context(state):
            assert _active_component_context.get() is state.context
            raise ValueError("boom")

        assert _active_component_context.get(None) is None
        assert _active_effect_scope.get(None) is None
        assert _active_scope.get(None) is None

    def test_nested_activation_restores_parent(self):
        parent_state = _make_state("Parent")
        child_state = _make_state("Child")

        with component_context(parent_state):
            assert _active_component_context.get() is parent_state.context
            with component_context(child_state):
                assert _active_component_context.get() is child_state.context
                assert _active_effect_scope.get() is child_state.effect_scope
                assert _active_scope.get() is child_state.effect_scope
            assert _active_component_context.get() is parent_state.context
            assert _active_effect_scope.get() is parent_state.effect_scope
            assert _active_scope.get() is parent_state.effect_scope

        assert _active_component_context.get(None) is None
        assert _active_effect_scope.get(None) is None
        assert _active_scope.get(None) is None
