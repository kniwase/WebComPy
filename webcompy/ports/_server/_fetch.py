from __future__ import annotations

import contextlib

import httpx

from webcompy.ports._fetch import FetchPort, Response


class ServerFetchPort(FetchPort):
    def __init__(self) -> None:
        self._client = httpx.AsyncClient()

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        res = await self._client.request(method, url, headers=headers, content=body)
        return Response(
            text=res.text,
            headers=dict(res.headers),
            status_code=res.status_code,
            status_text=res.reason_phrase,
            ok=res.is_success,
        )

    async def close(self) -> None:
        await self._client.aclose()

    def __del__(self) -> None:
        import asyncio

        with contextlib.suppress(RuntimeError, ImportError, ModuleNotFoundError):
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._client.aclose())  # noqa: F841, RUF006
