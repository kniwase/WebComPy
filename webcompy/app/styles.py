"""Reactive app-level style helpers.

Public API:
    reactive_style(selector, vars_dict) -> Computed[str]
        Build a CSS rule like ``":root { --x: v; --y: w; }"`` from a mapping
        of CSS-variable names to reactive values. Values may be plain
        strings, ``SignalBase[str]`` instances, or callables returning
        strings. The returned ``Computed[str]`` re-evaluates whenever any
        tracked signal changes.

    reactive_block(selector, content) -> Computed[str]
        Build ``"{selector} { {content} }"`` where ``content`` is a single
        CSS block (e.g., one or more declarations). Useful for arbitrary
        CSS, not just variable declarations.

Both helpers return a ``Computed[str]`` suitable for passing to
``app.append_style(...)``. They can also be used directly wherever a
``Computed[str]`` is expected.

Example:
    >>> from webcompy.app import WebComPyApp, WebComPyAppConfig
    >>> from webcompy.app.styles import reactive_style
    >>> from webcompy.signal import Signal
    >>>
    >>> app = WebComPyApp(...)
    >>> accent = Signal("#0969da")
    >>> app.append_style(reactive_style(":root", {
    ...     "--color-accent": accent,
    ...     "--color-bg": "white",
    ... }))
    >>>
    >>> # later: accent.value = "#ff0000"  # CSS variable updates everywhere
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TypeAlias

from webcompy.signal import Computed, SignalBase
from webcompy.signal._computed import Computed as _Computed

ReactiveValue: TypeAlias = str | SignalBase[str] | Callable[[], str]
VarsMapping: TypeAlias = Mapping[str, ReactiveValue]


def _resolve_value(v: ReactiveValue) -> str:
    if isinstance(v, str):
        return v
    if isinstance(v, SignalBase):
        return v.value
    return v()


def reactive_style(selector: str, vars: VarsMapping) -> Computed[str]:
    """Build ``{selector} { --x: v; --y: w; }`` from a var name -> value mapping.

    Values may be plain strings, ``SignalBase[str]`` instances, or callables
    returning strings. The returned ``Computed[str]`` re-evaluates whenever
    any tracked signal changes.

    Example:
        >>> app.append_style(reactive_style(":root", {
        ...     "--color-accent": Signal("#0969da"),
        ...     "--color-bg": "white",
        ... }))
    """
    items = list(vars.items())

    def _render() -> str:
        if not items:
            return ""
        body = "\n  ".join(f"{name}: {_resolve_value(v)};" for name, v in items)
        return f"{selector} {{\n  {body}\n}}"

    return _Computed(_render)


def reactive_block(selector: str, content: ReactiveValue) -> Computed[str]:
    """Build ``{selector} { {content} }`` where content is a single CSS block.

    Useful for arbitrary CSS, not just variable declarations. ``content`` may
    be a plain string, a ``SignalBase[str]``, or a callable returning a
    string.

    Example:
        >>> app.append_style(reactive_block("body", computed(lambda: f"color: {fg.value};")))
    """
    return _Computed(lambda: f"{selector} {{\n{_resolve_value(content)}\n}}")


__all__ = [
    "ReactiveValue",
    "VarsMapping",
    "reactive_block",
    "reactive_style",
]
