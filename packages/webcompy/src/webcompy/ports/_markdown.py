from __future__ import annotations

from abc import ABC, abstractmethod


class MarkdownPort(ABC):
    @abstractmethod
    def render(self, source: str) -> str: ...
