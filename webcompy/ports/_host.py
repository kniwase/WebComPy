from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar, overload

T_co = TypeVar("T_co", covariant=True)


class HostPort(ABC):
    @abstractmethod
    def schedule_macro_task(self, callback: Callable[..., Any]) -> None: ...

    @overload
    @abstractmethod
    def create_js_global_getter(self, name: str, *, wrapper: Callable[[Any | None], T_co]) -> Callable[[], T_co]: ...

    @overload
    @abstractmethod
    def create_js_global_getter(self, name: str, *, default: T_co) -> Callable[[], Any | T_co]: ...

    @overload
    @abstractmethod
    def create_js_global_getter(
        self,
        name: str,
    ) -> Callable[[], Any | None]: ...

    @abstractmethod
    def create_js_global_getter(
        self,
        name: str,
        *,
        wrapper: Callable[[Any | None], Any] | None = None,
        default: Any = None,
    ) -> Callable[[], Any]: ...
