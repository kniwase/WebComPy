from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConsoleMessage:
    type: str
    text: str
    location: str

    def format(self) -> str:
        return f"[{self.type}] {self.text} ({self.location})"
