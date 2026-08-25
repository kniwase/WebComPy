"""Browser WebSocket port using the native ``WebSocket``."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from webcompy.exception import WebComPyException
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._websocket import WebSocketConnection, WebSocketPort
from webcompy.utils._environment import ENVIRONMENT


class BrowserWebSocketConnection(WebSocketConnection):
    def __init__(self, ws: Any, cleanup: Callable[[], None]) -> None:
        self._ws = ws
        self._cleanup = cleanup
        self._closed = False

    def send(self, data: str) -> None:
        if self._closed:
            return
        self._ws.send(data)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._cleanup()


class BrowserWebSocketPort(WebSocketPort):
    def __init__(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserWebSocketPort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser

    def open(
        self,
        url: str,
        *,
        protocols: tuple[str, ...] = (),
        on_open: Callable[[], None],
        on_message: Callable[[str], None],
        on_binary: Callable[[], None],
        on_error: Callable[[], None],
        on_close: Callable[[int, str, bool], None],
    ) -> WebSocketConnection:
        ffi = self._browser.pyscript.ffi
        if protocols:
            ws = self._browser.window.WebSocket.new(url, ffi.to_js(list(protocols)))
        else:
            ws = self._browser.window.WebSocket.new(url)

        def _open_handler(_event: Any) -> None:
            on_open()

        def _error_handler(_event: Any) -> None:
            on_error()

        def _message_handler(event: Any) -> None:
            data = event.data
            if isinstance(data, str):
                on_message(data)
            else:
                on_binary()

        def _close_handler(event: Any) -> None:
            on_close(int(event.code), str(event.reason), bool(event.wasClean))

        proxies: list[Any] = []
        try:
            open_proxy = ffi.create_proxy(_open_handler)
            proxies.append(open_proxy)
            error_proxy = ffi.create_proxy(_error_handler)
            proxies.append(error_proxy)
            message_proxy = ffi.create_proxy(_message_handler)
            proxies.append(message_proxy)
            close_proxy = ffi.create_proxy(_close_handler)
            proxies.append(close_proxy)
            ws.addEventListener("open", open_proxy)
            ws.addEventListener("error", error_proxy)
            ws.addEventListener("message", message_proxy)
            ws.addEventListener("close", close_proxy)
        except Exception:
            for proxy in proxies:
                if hasattr(proxy, "destroy"):
                    proxy.destroy()
            ws.close()
            raise

        def _cleanup() -> None:
            ws.removeEventListener("open", open_proxy)
            ws.removeEventListener("error", error_proxy)
            ws.removeEventListener("message", message_proxy)
            ws.removeEventListener("close", close_proxy)
            for proxy in (open_proxy, error_proxy, message_proxy, close_proxy):
                if hasattr(proxy, "destroy"):
                    proxy.destroy()
            ws.close()

        return BrowserWebSocketConnection(ws, _cleanup)
