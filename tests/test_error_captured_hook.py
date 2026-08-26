from __future__ import annotations

import pytest

from webcompy.components import ComponentContext, define_component, on_error_captured
from webcompy.components._hooks import _active_component_context
from webcompy.components._libs import Context
from webcompy.elements import html
from webcompy_testing import TestRenderer


def _make_context() -> Context:
    return Context(
        props=None,
        slots={},
        component_name="TestComponent",
        title_getter=lambda: "",
        meta_getter=lambda: {},
        title_setter=lambda x: None,
        meta_setter=lambda k, v: None,
    )


class TestOnErrorCapturedRegistration:
    def test_context_accumulates_hooks_in_registration_order(self):
        ctx = _make_context()

        def hook_a(err: Exception):
            return None

        def hook_b(err: Exception):
            return False

        ctx.on_error_captured(hook_a)
        ctx.on_error_captured(hook_b)

        assert ctx._error_captured_hooks == [hook_a, hook_b]

    def test_module_function_registers_on_active_context(self):
        ctx = _make_context()

        def hook(err: Exception):
            return None

        token = _active_component_context.set(ctx)
        try:
            returned = on_error_captured(hook)
        finally:
            _active_component_context.reset(token)

        assert returned is hook
        assert ctx._error_captured_hooks == [hook]

    def test_registration_outside_setup_raises_lookup_error(self):
        def hook(err: Exception):
            return None

        with pytest.raises(LookupError):
            on_error_captured(hook)


_captured_hooks_seen: list[object] = []


@define_component()
def HookedComponent(context: ComponentContext[None]):
    def hook(err: Exception):
        return None

    context.on_error_captured(hook)
    _captured_hooks_seen.append(hook)
    return html.DIV({"data-testid": "hooked"}, "hooked")


class TestComponentHookStorage:
    def test_component_stores_hooks_registered_during_setup(self):
        _captured_hooks_seen.clear()
        with TestRenderer.render(HookedComponent) as result:
            instance = result._instance
            assert instance._error_captured_hooks == _captured_hooks_seen
            assert len(instance._error_captured_hooks) == 1

    def test_hooks_released_on_destroy(self):
        _captured_hooks_seen.clear()
        with TestRenderer.render(HookedComponent) as result:
            instance = result._instance
            assert instance._error_captured_hooks
            instance._remove_element()
            assert instance._error_captured_hooks == []
