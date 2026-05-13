from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from json import loads as json_loads
from typing import Any


@dataclass
class Response:
    text: str
    headers: dict[str, str]
    status_code: int
    status_text: str
    ok: bool

    def raise_for_status(self) -> None:
        if not self.ok:
            raise Exception("HTTP error")

    def json(self, **kwargs: Any) -> Any:
        return json_loads(self.text, **kwargs)


class FetchPort(ABC):
    @abstractmethod
    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response: ...
