from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
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
    content: bytes = b""

    def raise_for_status(self) -> None:
        if not self.ok:
            raise Exception("HTTP error")

    def json(self, **kwargs: Any) -> Any:
        return json_loads(self.text, **kwargs)


class FetchStream(ABC):
    """A streaming HTTP response.

    ``status_code`` / ``headers`` / ``ok`` are available immediately after
    the request is opened, without consuming the response body. Iteration
    yields text chunks whose concatenation equals the complete body text.
    ``close()`` (and ``aclose()``) abort the underlying request, are
    idempotent, and finish in-flight iteration without yielding further
    chunks.
    """

    def __init__(self, status_code: int, headers: dict[str, str], ok: bool) -> None:
        self.status_code = status_code
        self.headers = headers
        self.ok = ok
        self._closed = False

    def close(self) -> None:
        self._closed = True

    async def aclose(self) -> None:
        self.close()

    def __aiter__(self) -> AsyncIterator[str]:
        return self

    @abstractmethod
    async def __anext__(self) -> str: ...


class _BufferedFetchStream(FetchStream):
    def __init__(self, status_code: int, headers: dict[str, str], ok: bool, text: str) -> None:
        super().__init__(status_code, headers, ok)
        self._text = text
        self._yielded = False

    async def __anext__(self) -> str:
        if self._closed or self._yielded:
            raise StopAsyncIteration
        self._yielded = True
        return self._text


class FetchPort(ABC):
    @abstractmethod
    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        """Perform an HTTP request.

        Args:
            url: Target URL.
            method: HTTP method (default ``"GET"``).
            headers: Optional request headers.
            body: Optional request body.

        Returns:
            A ``Response`` object with text, headers, and status.

        """
        ...

    async def stream(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> FetchStream:
        """Open a streaming HTTP request.

        The default implementation performs an ordinary ``fetch()`` and
        yields the entire response body as a single chunk. Implementations
        MAY override this method for real incremental streaming.

        Args:
            url: Target URL.
            method: HTTP method (default ``"GET"``).
            headers: Optional request headers.
            body: Optional request body.

        Returns:
            A ``FetchStream`` with response metadata and an async iterator of
            body text chunks.

        """
        res = await self.fetch(url, method=method, headers=headers, body=body)
        return _BufferedFetchStream(res.status_code, res.headers, res.ok, res.text)

    def is_self_site_url(self, url: str) -> bool:
        """Return whether *url* is a self-site URL (relative to the same application).

        The default implementation returns ``False`` for all URLs.
        Subclasses (e.g. ``ServerFetchPort``) override this to return
        ``True`` for URLs starting with ``/`` or ``.``.
        """
        return False
