from __future__ import annotations

import contextlib
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
        self._apply_to_html(self._signal.value)

    @property
    def signal(self) -> Signal[Theme]:
        return self._signal

    @property
    def value(self) -> Theme:
        return self._signal.value

    def set(self, theme: Theme) -> None:
        self._signal.value = theme
        write_theme_cookie_value(theme)
        self._apply_to_html(theme)

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

    def _apply_to_html(self, theme: Theme) -> None:
        if theme is Theme.SYSTEM:
            with contextlib.suppress(Exception):
                self._render_context.remove_html_attr("data-theme")
        else:
            with contextlib.suppress(Exception):
                self._render_context.set_html_attr("data-theme", theme.value)


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
