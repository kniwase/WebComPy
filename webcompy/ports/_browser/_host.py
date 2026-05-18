from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, overload

from webcompy.exception import WebComPyException
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._host import HostPort
from webcompy.utils._environment import ENVIRONMENT

T_co = TypeVar("T_co", covariant=True)


class BrowserHostPort(HostPort):
    def __init__(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserHostPort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser

    def schedule_macro_task(self, callback: Callable[..., Any]) -> None:
        self._browser.window.setTimeout(callback, 0)

    @overload
    def create_js_global_getter(self, name: str, *, wrapper: Callable[[Any | None], T_co]) -> Callable[[], T_co]: ...
    @overload
    def create_js_global_getter(self, name: str, *, default: T_co) -> Callable[[], Any | T_co]: ...
    @overload
    def create_js_global_getter(self, name: str) -> Callable[[], Any | None]: ...
    def create_js_global_getter(
        self,
        name: str,
        *,
        wrapper: Callable[[Any | None], Any] | None = None,
        default: Any = None,
    ) -> Callable[[], Any]:
        def _getter() -> Any:
            value = getattr(self._browser.window, name, None)
            if wrapper is not None:
                return wrapper(value)
            if value is None:
                return default
            return value

        return _getter
