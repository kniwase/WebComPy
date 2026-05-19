from __future__ import annotations

import contextlib
from typing import Any, Literal

from webcompy.exception import WebComPyException
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._history import HistoryPort
from webcompy.signal._base import SignalBase
from webcompy.utils._environment import ENVIRONMENT


class BrowserHistoryPort(HistoryPort):
    def __init__(self, *, mode: Literal["hash", "history"]) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserHistoryPort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser
        super().__init__(self._compute_initial_path(mode), mode=mode)
        self._popstate_handler_proxy = self._browser.pyscript.ffi.create_proxy(self._on_popstate)
        self._browser.window.addEventListener("popstate", self._popstate_handler_proxy)

    def _compute_initial_path(self, mode: Literal["hash", "history"]) -> str:
        location = self._browser.window.location
        if mode == "history":
            return location.pathname + location.search
        hash_val = location.hash
        return hash_val[1:] if hash_val.startswith("#") else hash_val

    def _on_popstate(self, event: object) -> None:
        location = self._browser.window.location
        if self._mode == "history":
            path = location.pathname + location.search
        else:
            hash_val = location.hash
            path = hash_val[1:] if hash_val.startswith("#") else hash_val
        hist_state = self._browser.window.history.state
        state: dict[str, Any] | None = None
        if hist_state is not None and not self._browser.pyscript.ffi.is_none(hist_state):
            state = hist_state.to_dict()
        if self._navigation_callback is not None:
            self._navigation_callback(path, state)
        else:
            self._do_navigate(path, state)

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._browser.window.removeEventListener("popstate", self._popstate_handler_proxy)
            self._popstate_handler_proxy.destroy()

    def current_search(self) -> str:
        return self._browser.window.location.search

    def history_state(self) -> object | None:
        return self._browser.window.history.state

    @SignalBase._change_event
    def refresh_from_window(self) -> None:
        location = self._browser.window.location
        if self._mode == "history":
            self._value = location.pathname + location.search
        else:
            hash_val = location.hash
            self._value = hash_val[1:] if hash_val.startswith("#") else hash_val
        hist_state = self._browser.window.history.state
        if hist_state is not None and not self._browser.pyscript.ffi.is_none(hist_state):
            self._state = hist_state.to_dict()
        else:
            self._state = None
