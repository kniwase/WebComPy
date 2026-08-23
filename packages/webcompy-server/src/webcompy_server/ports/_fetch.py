from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from webcompy.exception import WebComPyException
from webcompy.hydration._payload import TransferFetchEntry
from webcompy.ports._fetch import FetchPort, Response

if TYPE_CHECKING:
    from starlette.types import ASGIApp


class ServerFetchPort(FetchPort):
    """Server-side ``FetchPort``.

    ``noop = True`` marks this port as a pure no-op for realtime
    connections: ``use_event_source`` (non-GET) uses it as the signal that
    SSR/SSG degradation (warning + empty closed handle) applies, rather than
    issuing a fetch request through the port. The port itself remains fully
    functional for ordinary ``fetch()`` calls during SSR/SSG.
    """

    noop = True

    def __init__(self, external_client: httpx.AsyncClient | None = None) -> None:
        self._external_client = external_client
        self._prototype: ServerFetchPort | None = None
        self._self_site_client: httpx.AsyncClient | None = None
        self._asgi_app: ASGIApp | None = None
        self._blocked_paths: list[str] = []
        self._mount_prefixes: list[str] = []
        self._base_url: str = "/"
        self._embedded: bool = False
        self._response_cache: dict[str, Response] = {}

    def is_self_site_url(self, url: str) -> bool:
        if url.startswith("//"):
            return False
        return url.startswith("/") or url.startswith(".")

    def configure(
        self,
        asgi_app: ASGIApp,
        blocked_paths: list[str] | None = None,
        base_url: str | None = None,
        mount_prefixes: list[str] | None = None,
        *,
        embedded: bool = False,
    ) -> None:
        if self._asgi_app is not None:
            raise WebComPyException("ServerFetchPort is already configured")
        self._asgi_app = asgi_app
        self._blocked_paths = blocked_paths or []
        self._mount_prefixes = ["/" + p.strip("/") for p in (mount_prefixes or []) if p.strip("/")]
        if base_url is not None:
            self._base_url = base_url
        self._embedded = embedded
        self._self_site_client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=asgi_app),
        )

    def _is_mount_path(self, path: str) -> bool:
        clean_path = path.split("?", 1)[0].split("#", 1)[0]
        return any(clean_path == prefix or clean_path.startswith(prefix + "/") for prefix in self._mount_prefixes)

    def _resolve_self_site_path(self, url: str) -> str:
        if self._embedded:
            if url.startswith("."):
                base = self._base_url.rstrip("/")
                url = url.lstrip(".")
                url = url.lstrip("/")
                return f"{base}/{url}" if base else f"/{url}"
            return url
        if url.startswith("/") and self._is_mount_path(url):
            return url
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

    def _cache_key(self, url: str, method: str, body: str | None = None) -> str:
        if method == "GET":
            return url
        return f"{method}:{url}:{body or ''}"

    @staticmethod
    def _extract_url_from_cache_key(key: str) -> str:
        for method in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
            prefix = f"{method}:"
            if key.startswith(prefix):
                return key[len(prefix) :].rsplit(":", 1)[0]
        return key

    def _ensure_external_client(self) -> httpx.AsyncClient:
        if self._external_client is None:
            self._external_client = httpx.AsyncClient()
        return self._external_client

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        if not self.is_self_site_url(url):
            client = (
                self._prototype._ensure_external_client()
                if self._prototype is not None
                else self._ensure_external_client()
            )
            res = await client.request(method, url, headers=headers, content=body)
            return Response(
                text=res.text,
                content=res.content,
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
        cache_key = self._cache_key(resolved_path, method, body)
        if cache_key in self._response_cache:
            return self._response_cache[cache_key]

        if not self._is_mount_path(resolved_path) and self._is_blocked(resolved_path):
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
        response = Response(
            text=res.text,
            content=res.content,
            headers=dict(res.headers),
            status_code=res.status_code,
            status_text=res.reason_phrase,
            ok=res.is_success,
        )
        self._response_cache[cache_key] = response
        return response

    def _clone_for_context(self) -> ServerFetchPort:
        clone = ServerFetchPort(external_client=self._external_client)
        clone._prototype = self
        clone._asgi_app = self._asgi_app
        clone._blocked_paths = self._blocked_paths
        clone._mount_prefixes = self._mount_prefixes
        clone._base_url = self._base_url
        clone._embedded = self._embedded
        clone._self_site_client = self._self_site_client
        return clone

    def get_transfer_data(self) -> dict[str, TransferFetchEntry]:
        result: dict[str, TransferFetchEntry] = {}
        for key, response in self._response_cache.items():
            url = self._extract_url_from_cache_key(key)
            if not self.is_self_site_url(url):
                continue
            if response.status_code == 204 or not response.text:
                continue
            result[key] = TransferFetchEntry(
                status_code=response.status_code,
                headers=response.headers,
                body=response.text,
            )
        return result

    def clear_cache(self) -> None:
        self._response_cache.clear()

    async def close(self) -> None:
        if self._external_client is not None:
            await self._external_client.aclose()
        if self._self_site_client is not None:
            await self._self_site_client.aclose()
