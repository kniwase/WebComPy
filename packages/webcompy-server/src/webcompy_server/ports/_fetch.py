from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import httpx

from webcompy.exception import WebComPyException
from webcompy.ports._fetch import FetchPort, Response

if TYPE_CHECKING:
    from starlette.types import ASGIApp


class ServerFetchPort(FetchPort):
    def __init__(self) -> None:
        self._external_client = httpx.AsyncClient()
        self._self_site_client: httpx.AsyncClient | None = None
        self._asgi_app: ASGIApp | None = None
        self._blocked_paths: list[str] = []
        self._base_url: str = "/"

    def is_self_site_url(self, url: str) -> bool:
        if url.startswith("//"):
            return False
        return url.startswith("/") or url.startswith(".")

    def configure(
        self,
        asgi_app: ASGIApp,
        blocked_paths: list[str] | None = None,
        base_url: str | None = None,
    ) -> None:
        if self._asgi_app is not None:
            raise WebComPyException("ServerFetchPort is already configured")
        self._asgi_app = asgi_app
        self._blocked_paths = blocked_paths or []
        if base_url is not None:
            self._base_url = base_url
        self._self_site_client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=asgi_app),
        )

    def _resolve_self_site_path(self, url: str) -> str:
        base = self._base_url.rstrip("/")
        if url.startswith("."):
            url = url.lstrip(".")
            url = url.lstrip("/")
            return f"{base}/{url}" if base else f"/{url}"
        return f"{base}{url}" if base else url

    def _is_blocked(self, path: str) -> bool:
        if path in self._blocked_paths:
            return True
        path_segments = path.strip("/").split("/")
        for blocked in self._blocked_paths:
            blocked_clean = blocked.strip("/")
            blocked_segments = blocked_clean.split("/")
            if len(path_segments) != len(blocked_segments):
                continue
            match = True
            for ps, bs in zip(path_segments, blocked_segments, strict=False):
                if bs.startswith(":"):
                    continue
                if ps != bs:
                    match = False
                    break
            if match:
                return True
        return False

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        if not self.is_self_site_url(url):
            res = await self._external_client.request(method, url, headers=headers, content=body)
            return Response(
                text=res.text,
                headers=dict(res.headers),
                status_code=res.status_code,
                status_text=res.reason_phrase,
                ok=res.is_success,
            )

        if self._asgi_app is None:
            return Response(
                text="ServerFetchPort is not configured. Call configure() before fetching self-site URLs.",
                headers={},
                status_code=500,
                status_text="Internal Server Error",
                ok=False,
            )

        resolved_path = self._resolve_self_site_path(url)

        if self._is_blocked(resolved_path):
            return Response(
                text=(
                    f"Path '{resolved_path}' is blocked during server-side rendering "
                    f"because it matches a page route. Fetching a page URL during SSR "
                    f"would cause infinite recursion."
                ),
                headers={},
                status_code=500,
                status_text="Internal Server Error",
                ok=False,
            )

        assert self._self_site_client is not None
        request_url = f"http://webcompy-internal{resolved_path}"
        res = await self._self_site_client.request(
            method,
            request_url,
            headers=headers,
            content=body,
        )
        return Response(
            text=res.text,
            headers=dict(res.headers),
            status_code=res.status_code,
            status_text=res.reason_phrase,
            ok=res.is_success,
        )

    async def close(self) -> None:
        await self._external_client.aclose()
        if self._self_site_client is not None:
            await self._self_site_client.aclose()

    def __del__(self) -> None:
        import asyncio

        with contextlib.suppress(RuntimeError, ImportError, ModuleNotFoundError):
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._external_client.aclose())  # noqa: RUF006
            if self._self_site_client is not None:
                task = loop.create_task(self._self_site_client.aclose())  # noqa: F841, RUF006
