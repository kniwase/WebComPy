from __future__ import annotations

import contextlib

from webcompy._browser._modules import browser as _raw_browser
from webcompy.exception import WebComPyException
from webcompy.ports._history import HistoryPort
from webcompy.signal._base import SignalBase
from webcompy.utils._environment import ENVIRONMENT


class BrowserHistoryPort(HistoryPort):
    def __init__(self, *, mode: str) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserHistoryPort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser
        initial_path = self._browser.window.location.pathname
        super().__init__(initial_path, mode=mode)
        self._popstate_handler_proxy = self._browser.pyscript.ffi.create_proxy(self._on_popstate)
        self._browser.window.addEventListener("popstate", self._popstate_handler_proxy)

    def _on_popstate(self, event: object) -> None:
        self.refresh_from_window()

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._browser.window.removeEventListener("popstate", self._popstate_handler_proxy)
            self._popstate_handler_proxy.destroy()

    def current_search(self) -> str:
        return self._browser.window.location.search

    def history_state(self) -> object | None:
        return self._browser.window.history.state

    def navigate(self, path: str) -> None:
        self._browser.window.history.pushState(None, "", path)
        self.refresh_from_window()

    @SignalBase._change_event
    def refresh_from_window(self) -> None:
        location = self._browser.window.location
        self._value = location.pathname + location.search + location.hash
