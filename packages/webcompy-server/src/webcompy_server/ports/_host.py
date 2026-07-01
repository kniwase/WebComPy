from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, overload

from webcompy.ports._host import HostPort

T_co = TypeVar("T_co", covariant=True)


class ServerHostPort(HostPort):
    def schedule_macro_task(self, callback: Callable[..., Any]) -> None:
        callback()

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
            if wrapper is not None:
                return wrapper(None)
            return default

        return _getter
