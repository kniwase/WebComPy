"""Reactive per-component scoped style.

Public API:
    reactive_scoped_style(func) -> ReactiveScopedStyle
        Create a reactive scoped style from a callable that returns the
        existing scoped-style dictionary shape (selector -> declarations).
        The callable is evaluated as a Computed: any Signal read inside it
        becomes a tracked dependency. When a tracked signal changes, the
        Computed re-evaluates and the corresponding <style> element's
        textContent is updated in the browser.

    ReactiveScopedStyle
        The class form. Useful for advanced use cases where you want to
        subclass and override the render_css(cid) method.

Registration:
    Inside a @define_component setup function, call
        context.use_reactive_scoped_style(style)
    This appends the style to the active ComponentGenerator's
    _reactive_styles list. The framework then emits one
    <style data-webcompy-cid-rx="{cid}-{index}"> element per reactive
    style in the document head, and updates its textContent on every
    change.

Example:
    >>> from webcompy.components import define_component, reactive_scoped_style
    >>> from webcompy.elements import html
    >>> from webcompy.signal import Signal
    >>>
    >>> @define_component
    ... def MyComponent(context):
    ...     color = Signal("blue")
    ...     context.use_reactive_scoped_style(
    ...         reactive_scoped_style(lambda: {".my-class": {"color": color.value}})
    ...     )
    ...     return html.DIV({}, "...")

Constraints:
    - The function must be synchronous (async functions raise TypeError).
    - Call use_reactive_scoped_style from inside a component setup; calling
      it from a non-component context raises WebComPyException.
    - Static ComponentGenerator.scoped_style (set via MyComp.scoped_style = {...})
      continues to work unchanged. Reactive and static styles coexist and
      render to separate <style> elements (static uses data-webcompy-cid,
      reactive uses data-webcompy-cid-rx).
"""

from __future__ import annotations

from collections.abc import Callable
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, Any, TypeAlias

from webcompy.components._libs import WebComPyComponentException
from webcompy.signal import Computed

if TYPE_CHECKING:
    from webcompy.components._generator import StyleDict


ReactiveScopedStyleFunc: TypeAlias = Callable[[], "dict[str, StyleDict]"]


_HELPERS_CACHE: tuple | None = None


def _get_helpers():
    global _HELPERS_CACHE
    if _HELPERS_CACHE is None:
        from webcompy.components._css_utils import _scope_selector
        from webcompy.components._generator import (
            _classify_nested_key,
            _process_style_declaration,
            _render_scoped_style_css,
        )

        _HELPERS_CACHE = (
            _classify_nested_key,
            _process_style_declaration,
            _render_scoped_style_css,
            _scope_selector,
        )
    return _HELPERS_CACHE


class ReactiveScopedStyle:
    _func: ReactiveScopedStyleFunc
    _cid: str | None
    _dict_computed: Computed[Any] | None
    _css_computed: Computed[str] | None
    _ref_count: int
    _subscription: Any | None
    _removed: bool

    def __init__(self, func: ReactiveScopedStyleFunc) -> None:
        if iscoroutinefunction(func):
            raise TypeError(
                "reactive_scoped_style function must be synchronous (no async def); Computed evaluation is synchronous"
            )
        self._func = func
        self._cid = None
        self._host_tag: str | None = None
        self._dict_computed = None
        self._css_computed = None
        self._ref_count = 0
        self._subscription = None
        self._removed = False

    def _bind(self, cid: str, host_tag: str | None = None) -> None:
        if self._cid is not None:
            if self._cid != cid:
                raise WebComPyComponentException(
                    f"ReactiveScopedStyle is already bound to a different component "
                    f"(was '{self._cid}', attempted '{cid}')"
                )
            return
        self._cid = cid
        self._host_tag = host_tag
        self._dict_computed = Computed(self._func)
        self._css_computed = Computed(lambda: self.render_css(self._cid or ""))

    def increment_ref(self) -> int:
        self._ref_count += 1
        return self._ref_count

    def decrement_ref(self) -> int:
        if self._ref_count > 0:
            self._ref_count -= 1
        return self._ref_count

    @property
    def ref_count(self) -> int:
        return self._ref_count

    @property
    def subscription(self) -> Any | None:
        return self._subscription

    def set_subscription(self, subscription: Any) -> None:
        self._subscription = subscription

    def mark_removed(self) -> None:
        self._removed = True

    @property
    def is_removed(self) -> bool:
        return self._removed

    @property
    def dict_computed(self) -> Computed[Any]:
        if self._dict_computed is None:
            raise WebComPyComponentException(
                "ReactiveScopedStyle is not bound to a component; "
                "call use_reactive_scoped_style() from inside a @define_component setup"
            )
        return self._dict_computed

    @property
    def css_computed(self) -> Computed[str]:
        if self._css_computed is None:
            raise WebComPyComponentException(
                "ReactiveScopedStyle is not bound to a component; "
                "call use_reactive_scoped_style() from inside a @define_component setup"
            )
        return self._css_computed

    def render_css(self, cid: str) -> str:
        if self._dict_computed is None:
            return ""
        (
            _classify_nested_key,
            _process_style_declaration,
            _render_scoped_style_css,
            _scope_selector,
        ) = _get_helpers()
        style = self._dict_computed.value
        if not style:
            return ""
        scoped_items: list[tuple[str, dict[str, Any]]] = []
        for selector, declaration in style.items():
            if _classify_nested_key(selector.strip()) == "at-rule":
                processed_selector = selector.strip()
            else:
                processed_selector = _scope_selector(selector.strip(), cid, host_tag=self._host_tag)
            scoped_items.append((processed_selector, _process_style_declaration(declaration)))
        return _render_scoped_style_css(dict(scoped_items), cid, host_tag=self._host_tag)


def reactive_scoped_style(func: ReactiveScopedStyleFunc) -> ReactiveScopedStyle:
    return ReactiveScopedStyle(func)


__all__ = ["ReactiveScopedStyle", "reactive_scoped_style"]
