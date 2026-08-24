"""Browser fetch port on PyScript's ``fetch`` with streaming support."""

from __future__ import annotations

import contextlib
from typing import Any

from webcompy.exception import WebComPyException
from webcompy.hydration._payload import TransferFetchEntry
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._fetch import FetchPort, FetchStream, Response, _BufferedFetchStream
from webcompy.utils._environment import ENVIRONMENT


class _BrowserFetchStream(FetchStream):
    def __init__(
        self,
        status_code: int,
        headers: dict[str, str],
        ok: bool,
        reader: Any,
        decoder: Any,
        controller: Any,
    ) -> None:
        super().__init__(status_code, headers, ok)
        self._reader = reader
        self._decoder = decoder
        self._controller = controller
        self._done = False

    def close(self) -> None:
        if self._closed:
            return
        super().close()
        with contextlib.suppress(Exception):
            self._reader.cancel()
        self._controller.abort()

    async def __anext__(self) -> str:
        while True:
            if self._closed or self._done:
                raise StopAsyncIteration
            try:
                result = await self._reader.read()
            except Exception:
                if self._closed:
                    raise StopAsyncIteration from None
                raise
            if result.done:
                self._done = True
                tail = self._decoder.decode()
                if tail:
                    return tail
                raise StopAsyncIteration
            text = self._decoder.decode(bytes(result.value), stream=True)
            if text:
                return text


class BrowserFetchPort(FetchPort):
    def __init__(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserFetchPort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser
        self._response_cache: dict[str, Response] = {}

    def _cache_key(self, url: str, method: str, body: str | None = None) -> str:
        if method == "GET":
            return url
        return f"{method}:{url}:{body or ''}"

    def populate_from_transfer(self, data: dict[str, TransferFetchEntry]) -> None:
        for key, entry in data.items():
            self._response_cache[key] = Response(
                text=entry.body,
                headers=entry.headers,
                status_code=entry.status_code,
                status_text="OK" if entry.status_code < 400 else "Error",
                ok=entry.status_code < 400,
            )

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        cache_key = self._cache_key(url, method, body)
        if cache_key in self._response_cache:
            return self._response_cache[cache_key]

        req_headers: Any = None
        if headers:
            req_headers = self._browser.Headers.new()
            for key, value in headers.items():
                req_headers.set(key, value)
        res = await self._browser.fetch(url, method=method, headers=req_headers, body=body)

        headers_obj = res.headers
        cloned = res.clone()
        text = await res.text()
        try:
            array_buf = await cloned.arrayBuffer()
            content = bytes(array_buf)
        except Exception:
            content = text.encode("utf-8")
        response = Response(
            text=text,
            content=content,
            headers=dict(
                zip(
                    list(headers_obj.keys()),
                    list(headers_obj.values()),
                    strict=True,
                )
            ),
            status_code=res.status,
            status_text=res.statusText,
            ok=res.ok,
        )
        return response

    async def stream(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> FetchStream:
        controller = self._browser.AbortController.new()
        req_headers: Any = None
        if headers:
            req_headers = self._browser.Headers.new()
            for key, value in headers.items():
                req_headers.set(key, value)
        try:
            res = await self._browser.fetch(
                url,
                method=method,
                headers=req_headers,
                body=body,
                signal=controller.signal,
            )
        except BaseException:
            with contextlib.suppress(Exception):
                controller.abort()
            raise

        headers_obj = res.headers
        headers_dict = dict(
            zip(
                list(headers_obj.keys()),
                list(headers_obj.values()),
                strict=True,
            )
        )
        if res.body is None:
            return _BufferedFetchStream(res.status, headers_dict, res.ok, "")
        reader = res.body.getReader()
        decoder = self._browser.TextDecoder.new("utf-8")
        return _BrowserFetchStream(res.status, headers_dict, res.ok, reader, decoder, controller)
