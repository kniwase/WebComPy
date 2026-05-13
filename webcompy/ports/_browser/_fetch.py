from __future__ import annotations

from webcompy._browser._modules import browser as _raw_browser
from webcompy.exception import WebComPyException
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
        if headers:
            options["headers"] = self._browser.pyscript.ffi.create_proxy(headers)
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

        if headers:
            proxy = options.pop("headers", None)
            if proxy and hasattr(proxy, "destroy"):
                proxy.destroy()

        return response
