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
from typing import TYPE_CHECKING, Any, TypeAlias, cast

from webcompy.components._libs import WebComPyComponentException
from webcompy.signal._computed import Computed

if TYPE_CHECKING:
    from webcompy.components._generator import StyleDict


ReactiveScopedStyleFunc: TypeAlias = Callable[[], "StyleDict"]


def _get_helpers():
    from webcompy.components._generator import (
        _classify_nested_key,
        _generate_css_recursive,
        _process_style_declaration,
        _scope_combinator_selector,
    )

    return (
        _classify_nested_key,
        _generate_css_recursive,
        _process_style_declaration,
        _scope_combinator_selector,
    )


class ReactiveScopedStyle:
    _func: ReactiveScopedStyleFunc
    _cid: str | None
    _dict_computed: Computed[Any] | None
    _css_computed: Computed[str] | None

    def __init__(self, func: ReactiveScopedStyleFunc) -> None:
        if iscoroutinefunction(func):
            raise TypeError(
                "reactive_scoped_style function must be synchronous (no async def); Computed evaluation is synchronous"
            )
        self._func = func
        self._cid = None
        self._dict_computed = None
        self._css_computed = None

    def _bind(self, cid: str) -> None:
        if self._cid is not None:
            if self._cid != cid:
                raise WebComPyComponentException(
                    f"ReactiveScopedStyle is already bound to a different component "
                    f"(was '{self._cid}', attempted '{cid}')"
                )
            return
        self._cid = cid
        self._dict_computed = Computed(self._func)
        self._css_computed = Computed(lambda: self.render_css(self._cid or ""))

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
            _generate_css_recursive,
            _process_style_declaration,
            _scope_combinator_selector,
        ) = _get_helpers()
        style = self._dict_computed.value
        if not style:
            return ""
        scoped_items = self._apply_scope(style, cid)
        parts: list[str] = []
        for selector, style_dict in scoped_items.items():
            stripped = selector.strip()
            if stripped.startswith("@keyframes"):
                inner_parts: list[str] = []
                for inner_sel, inner_styles in style_dict.items():
                    inner_parts.append(
                        _generate_css_recursive(
                            inner_sel.strip(),
                            cast("dict[str, Any]", inner_styles),
                        )
                    )
                parts.append(f"{stripped} {{ {' '.join(inner_parts)} }}")
            elif _classify_nested_key(stripped) == "at-rule":
                inner_parts = self._render_at_rule_inner(style_dict, cid)
                parts.append(f"{stripped} {{ {' '.join(inner_parts)} }}")
            else:
                parts.append(
                    _generate_css_recursive(
                        selector,
                        cast("dict[str, Any]", style_dict),
                    )
                )
        body = " ".join(parts)
        if not body.strip():
            return ""
        return f"@layer webcompy-scope {{ {body} }}"

    def _apply_scope(self, style: Any, cid: str) -> dict[str, dict[str, Any]]:
        (
            _classify_nested_key,
            _generate_css_recursive,
            _process_style_declaration,
            _scope_combinator_selector,
        ) = _get_helpers()
        scoped_items: list[tuple[str, dict[str, Any]]] = []
        for selector, declaration in style.items():
            if _classify_nested_key(selector.strip()) == "at-rule":
                processed_selector = selector.strip()
            else:
                stripped = selector.strip()
                processed_selector = _scope_combinator_selector(stripped, cid)
            scoped_items.append((processed_selector, _process_style_declaration(declaration)))
        return dict(scoped_items)

    def _render_at_rule_inner(self, style_dict: Any, cid: str) -> list[str]:
        (
            _classify_nested_key,
            _generate_css_recursive,
            _process_style_declaration,
            _scope_combinator_selector,
        ) = _get_helpers()
        inner_parts: list[str] = []
        for inner_sel, inner_styles in style_dict.items():
            stripped_inner = inner_sel.strip()
            inner_type = _classify_nested_key(stripped_inner)
            if inner_type == "at-rule":
                if stripped_inner.startswith("@keyframes"):
                    key_parts: list[str] = []
                    for k, v in inner_styles.items():
                        key_parts.append(
                            _generate_css_recursive(
                                k.strip(),
                                cast("dict[str, Any]", v),
                            )
                        )
                    inner_parts.append(f"{stripped_inner} {{ {' '.join(key_parts)} }}")
                else:
                    nested_parts = self._render_at_rule_inner(cast("dict[str, Any]", inner_styles), cid)
                    inner_parts.append(f"{stripped_inner} {{ {' '.join(nested_parts)} }}")
            elif inner_type == "pseudo":
                scoped = f"*[webcompy-cid-{cid}]{stripped_inner}"
                inner_parts.append(
                    _generate_css_recursive(
                        scoped,
                        cast("dict[str, Any]", inner_styles),
                    )
                )
            elif inner_type == "combinator":
                scoped_inner = _scope_combinator_selector(stripped_inner, cid)
                inner_parts.append(
                    _generate_css_recursive(
                        scoped_inner,
                        cast("dict[str, Any]", inner_styles),
                    )
                )
            else:
                scoped_inner = f"{stripped_inner}[webcompy-cid-{cid}]"
                inner_parts.append(
                    _generate_css_recursive(
                        scoped_inner,
                        cast("dict[str, Any]", inner_styles),
                    )
                )
        return inner_parts


def reactive_scoped_style(func: ReactiveScopedStyleFunc) -> ReactiveScopedStyle:
    return ReactiveScopedStyle(func)


__all__ = ["ReactiveScopedStyle", "reactive_scoped_style"]
