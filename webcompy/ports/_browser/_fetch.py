from __future__ import annotations

from typing import Any

from webcompy.exception import WebComPyException
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._fetch import FetchPort, Response
from webcompy.utils._environment import ENVIRONMENT


class BrowserFetchPort(FetchPort):
    def __init__(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserFetchPort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
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
            response = Response(
                text=await res.text(),
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
