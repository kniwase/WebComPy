from __future__ import annotations

from typing import TYPE_CHECKING, Any

from webcompy.signal import Signal
from webcompy.ui.theme._cookie import (
    write_theme_cookie_value,
)
from webcompy.ui.theme._theme import Theme

if TYPE_CHECKING:
    from webcompy.app._app import WebComPyApp


class ThemeManager:
    def __init__(self, app: WebComPyApp, render_context: Any, initial: Theme) -> None:
        self._app = app
        self._render_context = render_context
        self._signal: Signal[Theme] = Signal(_normalize_initial(initial))
        from webcompy.signal import Computed

        self._css = Computed(self._build_theme_css)

    @property
    def signal(self) -> Signal[Theme]:
        return self._signal

    @property
    def value(self) -> Theme:
        return self._signal.value

    def register_style(self) -> None:
        """Register the reactive theme CSS with the render context.

        Must be called AFTER the AppDocumentRoot is created, because
        the head element is part of the root. The render context's
        ``_root`` attribute is None until the root is constructed.
        """
        self._app.append_style(self._css)

    def set(self, theme: Theme) -> None:
        self._signal.value = theme
        write_theme_cookie_value(theme)

    def toggle(self) -> None:
        self.set(self._resolved_toggle_target())

    def cycle(self) -> None:
        order: tuple[Theme, ...] = (Theme.LIGHT, Theme.DARK, Theme.SYSTEM)
        current = self._signal.value
        try:
            idx = order.index(current)
        except ValueError:
            idx = 0
        next_theme = order[(idx + 1) % len(order)]
        self.set(next_theme)

    def _resolved_toggle_target(self) -> Theme:
        current = self._signal.value
        if current is not Theme.SYSTEM:
            return Theme.DARK if current is Theme.LIGHT else Theme.LIGHT
        return _system_prefers_dark()

    def _build_theme_css(self) -> str:
        from webcompy.ui.theme._tokens import DARK_TOKENS, render_tokens_css

        theme = self._signal.value
        dark_body = render_tokens_css(DARK_TOKENS, important=True)
        if theme is Theme.LIGHT:
            return ""
        if theme is Theme.DARK:
            return f":root {{\n  {dark_body}\n}}"
        return f"@media (prefers-color-scheme: dark) {{\n  :root {{\n    {dark_body}\n  }}\n}}"


def _normalize_initial(initial: Any) -> Theme:
    if isinstance(initial, Theme):
        return initial
    if isinstance(initial, str):
        try:
            return Theme(initial.lower())
        except ValueError:
            return Theme.SYSTEM
    return Theme.SYSTEM


def _system_prefers_dark() -> Theme:
    return Theme.SYSTEM
