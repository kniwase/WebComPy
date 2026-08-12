from __future__ import annotations

from collections.abc import Callable
from typing import Any

from webcompy.exception import WebComPyException
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._dom import DOMNode
from webcompy.ports._transition import TransitionPort, TransitionStyle
from webcompy.utils._environment import ENVIRONMENT


class BrowserTransitionStyle:
    def __init__(self, style: Any) -> None:
        self._style = style

    def get_property_value(self, name: str) -> str:
        value = self._style.getPropertyValue(name)
        return str(value) if value is not None else ""


class BrowserTransitionPort(TransitionPort):
    def __init__(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserTransitionPort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser

    @property
    def enabled(self) -> bool:
        return True

    def schedule_next_frame(self, callback: Callable[[], Any]) -> Callable[[], None]:
        window = self._browser.window
        first_id: Any = None
        second_id: Any = None

        def _second(*_args: Any) -> None:
            callback()

        def _first(*_args: Any) -> None:
            nonlocal first_id
            first_id = window.requestAnimationFrame(_second)

        first_id = window.requestAnimationFrame(_first)

        def _cancel() -> None:
            if first_id is not None:
                window.cancelAnimationFrame(first_id)
            if second_id is not None:
                window.cancelAnimationFrame(second_id)

        return _cancel

    def schedule_timeout(
        self,
        callback: Callable[[], Any],
        delay_ms: float,
    ) -> Callable[[], None]:
        window = self._browser.window
        timer_id = window.setTimeout(callback, delay_ms)

        def _cancel() -> None:
            window.clearTimeout(timer_id)

        return _cancel

    def get_computed_style(self, node: DOMNode) -> TransitionStyle:
        style = self._browser.window.getComputedStyle(node)
        return BrowserTransitionStyle(style)
