from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FFIPort(ABC):
    @abstractmethod
    def create_proxy(self, obj: Any) -> Any: ...
    @abstractmethod
    def destroy_proxy(self, proxy: Any) -> None: ...
    @abstractmethod
    def is_none(self, obj: Any) -> bool: ...
    @abstractmethod
    def to_js(self, obj: Any) -> Any: ...
    @abstractmethod
    def assign(self, target: Any, source: Any) -> None: ...
