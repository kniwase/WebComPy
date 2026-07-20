from __future__ import annotations

from typing import Any

from webcompy.exception import WebComPyException
from webcompy.hydration._payload import TransferFetchEntry
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._fetch import FetchPort, Response
from webcompy.utils._environment import ENVIRONMENT


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

        options: dict = {"method": method}
        headers_proxy: Any = None
        try:
            if headers:
                headers_proxy = self._browser.pyscript.ffi.create_proxy(headers)
                options["headers"] = headers_proxy
            if body:
                options["body"] = body

            res = await self._browser.fetch(url, **options)

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
        finally:
            if headers_proxy is not None and hasattr(headers_proxy, "destroy"):
                headers_proxy.destroy()

        return response
