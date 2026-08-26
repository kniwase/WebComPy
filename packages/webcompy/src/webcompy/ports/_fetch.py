"""HTTP fetch port with buffered and streaming responses."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from json import loads as json_loads
from typing import Any


@dataclass
class Response:
    """A buffered HTTP response returned by ``FetchPort.fetch``.

    Args:
        text: Response body decoded as text.
        headers: Response headers.
        status_code: HTTP status code.
        status_text: HTTP status text.
        ok: Whether the response is successful.
        content: Raw response body as bytes.

    Attributes:
        text: Response body decoded as text.
        headers: Response headers.
        status_code: HTTP status code.
        status_text: HTTP status text.
        ok: Whether the response is successful.
        content: Raw response body as bytes.

    """

    text: str
    headers: dict[str, str]
    status_code: int
    status_text: str
    ok: bool
    content: bytes = b""

    def raise_for_status(self) -> None:
        """Raise an exception when the response is not successful.

        Raises:
            Exception: If the response status is not successful.

        """
        if not self.ok:
            raise Exception("HTTP error")

    def json(self, **kwargs: Any) -> Any:
        """Decode the response body as JSON.

        Args:
            **kwargs: Extra keyword arguments forwarded to ``json.loads``.

        Returns:
            The decoded JSON value.

        """
        return json_loads(self.text, **kwargs)


class FetchStream(ABC):
    """A streaming HTTP response.

    Metadata (``status_code``, ``headers``, ``ok``) is available immediately
    after the request is opened, without consuming the response body.
    Iteration yields text chunks whose concatenation equals the complete
    body text. ``close()`` and ``aclose()`` abort the underlying request,
    are idempotent, and finish in-flight iteration without yielding further
    chunks.

    Args:
        status_code: HTTP status code of the streamed response.
        headers: Response headers.
        ok: Whether the response status code indicates success.

    Attributes:
        status_code: HTTP status code of the streamed response.
        headers: Response headers.
        ok: Whether the response status code indicates success.

    """

    def __init__(self, status_code: int, headers: dict[str, str], ok: bool) -> None:
        self.status_code = status_code
        self.headers = headers
        self.ok = ok
        self._closed = False

    def close(self) -> None:
        """Abort the underlying request and mark the stream closed.

        Idempotent; in-flight async iteration finishes without yielding
        further chunks.
        """
        self._closed = True

    async def aclose(self) -> None:
        """Asynchronous counterpart of ``close()``."""
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
    """HTTP client surface for buffered and streaming requests.

    Implementations perform real network requests (browser ``fetch``) or go
    through an in-process transport (server-side ASGI self-fetch).
    """

    @abstractmethod
    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | bytes | None = None,
    ) -> Response:
        """Perform an HTTP request.

        Args:
            url: Target URL.
            method: HTTP method (default ``"GET"``).
            headers: Optional request headers.
            body: Optional request body as text or bytes.

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
        body: str | bytes | None = None,
    ) -> FetchStream:
        """Open a streaming HTTP request.

        The default implementation performs an ordinary ``fetch()`` and
        yields the entire response body as a single chunk. Implementations
        MAY override this method for real incremental streaming.

        Args:
            url: Target URL.
            method: HTTP method (default ``"GET"``).
            headers: Optional request headers.
            body: Optional request body as text or bytes.

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

        Args:
            url: URL to classify.

        Returns:
            True if ``url`` is a self-site URL, False otherwise.

        """
        return False
