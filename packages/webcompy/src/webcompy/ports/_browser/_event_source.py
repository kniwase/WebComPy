"""Browser Server-Sent Events port using the native ``EventSource``."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from webcompy.exception import WebComPyException
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._event_source import EventSourcePort
from webcompy.utils._environment import ENVIRONMENT

_CLOSED_READY_STATE = 2


class BrowserEventSourcePort(EventSourcePort):
    def __init__(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserEventSourcePort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser

    def open(
        self,
        url: str,
        *,
        events: tuple[str, ...],
        on_open: Callable[[], None],
        on_message: Callable[[str, str, str], None],
        on_error: Callable[[], None],
        on_close: Callable[[], None],
    ) -> Callable[[], None]:
        ffi = self._browser.pyscript.ffi
        es = self._browser.window.EventSource.new(url)

        def _open_handler(_event: Any) -> None:
            on_open()

        def _error_handler(_event: Any) -> None:
            if int(es.readyState) == _CLOSED_READY_STATE:
                on_close()
            else:
                on_error()

        def _message_handler(event: Any) -> None:
            data = event.data
            last_event_id = event.lastEventId
            on_message(
                str(event.type),
                "" if ffi.is_none(data) else str(data),
                "" if ffi.is_none(last_event_id) else str(last_event_id),
            )

        proxies: list[Any] = []
        try:
            open_proxy = ffi.create_proxy(_open_handler)
            proxies.append(open_proxy)
            error_proxy = ffi.create_proxy(_error_handler)
            proxies.append(error_proxy)
            message_proxy = ffi.create_proxy(_message_handler)
            proxies.append(message_proxy)
            es.addEventListener("open", open_proxy)
            es.addEventListener("error", error_proxy)
            for event_type in events:
                es.addEventListener(event_type, message_proxy)
        except Exception:
            for proxy in proxies:
                if hasattr(proxy, "destroy"):
                    proxy.destroy()
            es.close()
            raise

        def _cleanup() -> None:
            es.removeEventListener("open", open_proxy)
            es.removeEventListener("error", error_proxy)
            for event_type in events:
                es.removeEventListener(event_type, message_proxy)
            for proxy in (open_proxy, error_proxy, message_proxy):
                if hasattr(proxy, "destroy"):
                    proxy.destroy()
            es.close()
            on_close()

        return _cleanup
