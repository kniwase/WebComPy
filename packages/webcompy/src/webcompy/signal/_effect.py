"""Side-effecting functions that re-run when their tracked signals change."""

from __future__ import annotations

import contextlib
import contextvars
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

from webcompy.di import InjectionError, inject
from webcompy.ports._keys import HOST_PORT_KEY
from webcompy.signal._graph import (
    SignalNode,
    _CallbackMixin,
    consumer_after_computation,
    consumer_before_computation,
    consumer_destroy,
    producer_mark_clean,
)

_active_scope: ContextVar[EffectScope | None] = ContextVar("_active_scope", default=None)

_pending_effects: list[EffectNode] = []
_scheduling_scheduled: bool = False


class EffectNode(SignalNode, _CallbackMixin):
    _fn: Callable[[], Any]
    _cleanup_fn: Callable[[], Any] | None
    _on_cleanup: Callable[[], Any] | None
    _disposed: bool

    def __init__(
        self,
        fn: Callable[[], Any],
        on_cleanup: Callable[[], Any] | None = None,
    ) -> None:
        super().__init__()
        self._fn = fn
        self._cleanup_fn = None
        self._on_cleanup = on_cleanup
        self._disposed = False
        self.consumer_is_always_live = True
        self._run()
        scope = _active_scope.get(None)
        if scope is not None:
            scope._effects.append(self)

    def _run(self) -> None:
        if self._disposed:
            return
        self._cleanup()
        prev = consumer_before_computation(self)
        try:
            result = self._fn()
            if callable(result):
                self._cleanup_fn = result
            elif self._on_cleanup is not None:
                self._cleanup_fn = self._on_cleanup
        except Exception:
            consumer_after_computation(self, prev)
            raise
        consumer_after_computation(self, prev)
        producer_mark_clean(self)

    def _cleanup(self) -> None:
        if self._cleanup_fn is not None:
            fn = self._cleanup_fn
            self._cleanup_fn = None
            with contextlib.suppress(Exception):
                fn()

    def producer_must_recompute(self) -> bool:
        return True

    def producer_recompute_value(self) -> None:
        self.dirty = False

    def _dispatch(self) -> None:
        _schedule_effect(self)


class EffectHandle:
    """Handle to a running effect, used to stop it."""

    _node: EffectNode

    def __init__(self, node: EffectNode) -> None:
        self._node = node

    def dispose(self) -> None:
        """Stop the effect permanently.

        The effect will not re-run for future signal changes; a pending
        cleanup function is invoked once.
        """
        if not self._node._disposed:
            self._node._disposed = True
            self._node._cleanup()
            consumer_destroy(self._node)


class EffectScope:
    """Container that collects effects and disposes them together."""

    _effects: list[EffectNode]

    def __init__(self) -> None:
        self._effects: list[EffectNode] = []

    def dispose(self) -> None:
        """Dispose all effects collected in this scope."""
        for effect in self._effects:
            if not effect._disposed:
                effect._disposed = True
                effect._cleanup()
                consumer_destroy(effect)
        self._effects.clear()


def effect(
    fn: Callable[[], Any],
    on_cleanup: Callable[[], Any] | None = None,
) -> EffectHandle:
    """Run ``fn`` and re-run it whenever a signal it read changes.

    Dependencies are tracked dynamically: each run records the signals
    the function reads, and a change to any of them schedules the next
    run. A callable returned by ``fn`` is treated as a cleanup function
    invoked before the next run and on disposal.

    Args:
        fn: The effect function. May return a cleanup callable.
        on_cleanup: Fallback cleanup callback used when ``fn`` returns a
            non-callable result.

    Returns:
        A handle that can stop the effect via ``dispose()``.

    """
    node = EffectNode(fn, on_cleanup)
    return EffectHandle(node)


def create_effect_scope() -> EffectScope:
    return EffectScope()


class _EffectScopeContextManager:
    def __init__(self, scope: EffectScope) -> None:
        self._scope = scope
        self._token: contextvars.Token[EffectScope | None] | None = None

    def __enter__(self) -> EffectScope:
        self._token = _active_scope.set(self._scope)
        return self._scope

    def __exit__(self, *args: Any) -> None:
        if self._token is not None:
            _active_scope.reset(self._token)


def effect_scope() -> _EffectScopeContextManager:
    scope = EffectScope()
    return _EffectScopeContextManager(scope)


def _schedule_effect(effect_node: EffectNode) -> None:
    global _scheduling_scheduled
    _pending_effects.append(effect_node)
    if not _scheduling_scheduled:
        try:
            inject(HOST_PORT_KEY).schedule_macro_task(_flush_pending_effects)
        except InjectionError:
            _scheduling_scheduled = False
            _run_effect_synchronously(effect_node)
        else:
            _scheduling_scheduled = True


def _flush_pending_effects() -> None:
    global _scheduling_scheduled
    _scheduling_scheduled = False
    effects = list(_pending_effects)
    _pending_effects.clear()
    for effect_node in effects:
        if not effect_node._disposed and effect_node.dirty:
            effect_node._run()


def _run_effect_synchronously(effect_node: EffectNode) -> None:
    if not effect_node._disposed and effect_node.dirty:
        effect_node._run()
