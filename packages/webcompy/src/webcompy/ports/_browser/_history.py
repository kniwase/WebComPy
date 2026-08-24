"""Browser history port driving ``history.pushState`` and popstate handling."""

from __future__ import annotations

import contextlib
import logging
from typing import Any, Literal

from webcompy.exception import WebComPyException
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._history import HistoryPort
from webcompy.signal import SignalBase
from webcompy.utils._environment import ENVIRONMENT
from webcompy.utils._serialize import is_json_seriarizable


class BrowserHistoryPort(HistoryPort):
    def __init__(self, *, mode: Literal["hash", "history"], base_url: str = "") -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserHistoryPort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser
        self._base_url = base_url.strip().strip("/")
        self._mode = mode
        super().__init__(self._normalize_path(self._compute_initial_path(mode)), mode=mode)
        self._popstate_handler_proxy = self._browser.pyscript.ffi.create_proxy(self._on_popstate)
        self._browser.window.addEventListener("popstate", self._popstate_handler_proxy)

    def _build_url(self, path: str) -> str:
        pathname, sep, query = path.partition("?")
        stripped = pathname.strip("/")
        url = f"/{stripped}/" if stripped else "/"
        if sep:
            url += "?" + query
        if self._mode == "hash":
            return "#" + url
        if self._base_url:
            return f"/{self._base_url}{url}"
        return url

    def _normalize_path(self, path: str) -> str:
        if self._mode == "hash" and path.startswith("#"):
            path = path[1:]
        base_url = getattr(self, "_base_url", "")
        if self._mode == "history" and base_url:
            prefix = f"/{base_url}"
            if path.startswith(prefix + "/") or path == prefix:
                path = path[len(prefix) :] or "/"
        pathname, sep, query = path.partition("?")
        if pathname and not pathname.endswith("/"):
            pathname += "/"
        return pathname + sep + query

    def _serialize_state(self, state: dict[str, Any] | None) -> dict[str, Any] | None:
        if state is not None and not is_json_seriarizable(state):
            logging.warning(
                "History state must be a json-serializable dict; passing None to the browser history entry."
            )
            return None
        return state

    def push_url(self, path: str, state: dict[str, Any] | None = None) -> None:
        self._browser.window.history.pushState(self._serialize_state(state), None, self._build_url(path))

    def replace_url(self, path: str, state: dict[str, Any] | None = None) -> None:
        self._browser.window.history.replaceState(self._serialize_state(state), None, self._build_url(path))

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
        path = self._normalize_path(path)
        hist_state = self._browser.window.history.state
        state: dict[str, Any] | None = None
        if hist_state is not None and not self._browser.pyscript.ffi.is_none(hist_state):
            state = hist_state.to_dict()
        old_value = self._value
        self._is_pop_dispatch = True
        try:
            if self._navigation_callback is not None:
                self._navigation_callback(path, state)
            else:
                self._do_navigate(path, state)
        finally:
            self._is_pop_dispatch = False
        manager = self._scroll_manager
        if manager is not None:
            manager.on_pop(old_value, path)

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
            path = location.pathname + location.search
        else:
            hash_val = location.hash
            path = hash_val[1:] if hash_val.startswith("#") else hash_val
        self._value = self._normalize_path(path)
        hist_state = self._browser.window.history.state
        if hist_state is not None and not self._browser.pyscript.ffi.is_none(hist_state):
            self._state = hist_state.to_dict()
        else:
            self._state = None
