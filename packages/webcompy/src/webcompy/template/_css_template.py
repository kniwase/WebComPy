"""CSS text helpers for component scoped and reactive styles."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from webcompy.components._generator import StyleDict
from webcompy.template._css_parser import parse_css
from webcompy.template._holes import resolve_holes


def css_text(source: str) -> dict[str, StyleDict]:
    """Convert a CSS text string into a selector-keyed ``dict[str, StyleDict]``.

    The returned dict matches the parameter type of
    ``ComponentGenerator.scoped_style``, so it can be assigned directly:

        MyComp.scoped_style = css_text(".btn { color: red; }")

    For file-based CSS, compose with ``await load_text(path)`` inside an
    async component setup:

        @define_component()
        async def CardPanel(ctx):
            css_src = await load_text("styles/card.css")
            CardPanel.scoped_style = css_text(css_src)
            return html.DIV(...)

    See ``parse_css`` for parsing details and limitations.

    Args:
        source: CSS source string.

    Returns:
        Selector-keyed dict whose values are ``StyleDict`` blocks.

    """
    return parse_css(source)


def css_text_template(
    source: str,
    context: dict[str, Any],
) -> Callable[[], dict[str, StyleDict]]:
    """Create a reactive CSS text factory supporting ``{{ }}`` interpolation.

    The returned factory resolves ``{{ varname }}`` / ``{{ a.b.c }}`` holes
    from ``context`` (via ``resolve_holes``), then parses the resolved CSS
    text. It is a plain synchronous ``Callable[[], dict[str, StyleDict]]``
    suitable for ``reactive_scoped_style``:

        color = Signal("blue")
        context.use_reactive_scoped_style(
            reactive_scoped_style(
                css_text_template(".btn { color: {{ c }}; }", {"c": color})
            )
        )

    The factory MUST NOT create its own ``Computed``. Dependency tracking is
    delegated to ``ReactiveScopedStyle``, which wraps the factory in a
    ``Computed``; ``resolve_holes`` reads ``Signal.value`` inside that
    closure, establishing the reactive graph.

    Because the factory is synchronous, file loading MUST happen outside it
    (``await load_text(path)`` in an async component setup before calling
    ``css_text_template``).

    Args:
        source: CSS source string with optional ``{{ }}`` holes.
        context: Mapping of variable names to values (strings, Signals,
            dataclasses, etc.). ``Signal.value`` is read at factory call time.

    Returns:
        A factory that resolves holes and parses CSS on each call.

    """

    def factory() -> dict[str, StyleDict]:
        return parse_css(resolve_holes(source, context))

    return factory
