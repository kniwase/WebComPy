from __future__ import annotations

from abc import ABC, abstractmethod


class CookiePort(ABC):
    @abstractmethod
    def get(self, name: str) -> str | None: ...
    @abstractmethod
    def set(
        self,
        name: str,
        value: str,
        *,
        max_age: int | None = None,
        path: str = "/",
        secure: bool = False,
        httponly: bool = False,
        samesite: str | None = None,
    ) -> None: ...
    @abstractmethod
    def delete(self, name: str, path: str = "/") -> None: ...
    @abstractmethod
    def get_all(self) -> dict[str, str]: ...
