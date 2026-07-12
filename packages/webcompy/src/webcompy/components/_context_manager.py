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
    context: Context[Any]
    effect_scope: EffectScope
    framework_cleanup: Callable[[], None]


@contextmanager
def component_context(state: ComponentRenderState) -> Generator[None, None, None]:
    ctx_token = _active_component_context.set(state.context)
    scope_token = _active_scope.set(state.effect_scope)
    try:
        yield
    finally:
        _active_component_context.reset(ctx_token)
        _active_scope.reset(scope_token)
