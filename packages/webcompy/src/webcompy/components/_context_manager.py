"""Component setup context management: render state dataclass and context manager."""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from webcompy.components._hooks import _active_component_context
from webcompy.components._libs import Context
from webcompy.signal import EffectScope
from webcompy.signal._effect import _active_scope


@dataclass
class ComponentRenderState:
    """Activation state bound to one component setup invocation.

    Carries the pieces of ambient state that must be active while the
    component's setup function (and its re-renders) run: the component
    ``Context`` proxy, the ``EffectScope`` collecting effects created
    during setup, and a cleanup callable disposing framework resources.

    Args:
        context: The component ``Context`` proxy for this component.
        effect_scope: Scope collecting effects created during setup.
        framework_cleanup: Callable disposing framework-owned resources.

    Attributes:
        context: The component ``Context`` proxy for this component.
        effect_scope: Scope collecting effects created during setup.
        framework_cleanup: Callable disposing framework-owned resources.

    """

    context: Context[Any]
    effect_scope: EffectScope
    framework_cleanup: Callable[[], None]


@contextmanager
def component_context(state: ComponentRenderState) -> Generator[None, None, None]:
    """Activate ``state`` for the duration of a ``with`` block.

    Inside the block, composables and lifecycle hooks target this
    component's context and effects join its effect scope.

    Args:
        state: Render state to activate.

    Returns:
        A context manager that restores the previous state upon exit.

    """
    ctx_token = _active_component_context.set(state.context)
    scope_token = _active_scope.set(state.effect_scope)
    try:
        yield
    finally:
        _active_component_context.reset(ctx_token)
        _active_scope.reset(scope_token)
