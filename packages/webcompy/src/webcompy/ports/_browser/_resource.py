from __future__ import annotations

import base64

from webcompy.di import inject
from webcompy.di._keys import RESOURCE_DATA_KEY
from webcompy.exception import WebComPyException
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy.ports._resource import ResourceNotFoundError, ResourcePort
from webcompy.utils._environment import ENVIRONMENT


class BrowserResourcePort(ResourcePort):
    def __init__(self, base_url: str) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserResourcePort is only available in browser environment")
        self._base_url = base_url.rstrip("/")

    def _resource_url(self, path: str) -> str:
        return f"{self._base_url}/_webcompy-resource/{path}"

    def _decode_payload(self, path: str) -> bytes | None:
        data = inject(RESOURCE_DATA_KEY, default={})
        encoded = data.get(path)
        if encoded is None:
            return None
        return base64.b64decode(encoded)

    async def _fetch_bytes(self, path: str) -> bytes:
        fetch_port = inject(FETCH_PORT_KEY, default=None)
        if fetch_port is None:
            raise ResourceNotFoundError(path, "browser", reason="no FetchPort in DI scope")
        url = self._resource_url(path)
        try:
            response = await fetch_port.fetch(url)
        except Exception as exc:
            raise ResourceNotFoundError(
                path,
                "browser",
                reason=f"payload miss and fetch failed: {exc}",
            ) from exc
        if not response.ok:
            raise ResourceNotFoundError(
                path,
                "browser",
                reason=(f"payload miss and fetch returned HTTP {response.status_code}"),
            )
        return response.text.encode("utf-8")

    async def load_text(self, path: str) -> str:
        payload = self._decode_payload(path)
        if payload is not None:
            return payload.decode("utf-8")
        content = await self._fetch_bytes(path)
        return content.decode("utf-8")

    async def load_bytes(self, path: str) -> bytes:
        payload = self._decode_payload(path)
        if payload is not None:
            return payload
        return await self._fetch_bytes(path)
