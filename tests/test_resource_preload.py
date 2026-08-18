from __future__ import annotations

import pytest

from webcompy.di import DIScope
from webcompy.di._keys import RESOURCE_DATA_KEY
from webcompy.ports._browser._resource import BrowserResourcePort
from webcompy.ports._fetch import FetchPort, Response
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy.ports._resource import ResourceNotFoundError
from webcompy_server.ports._resource import ServerResourcePort


class _CachingFetchPort(FetchPort):
    """Test double mimicking BrowserFetchPort's session response cache."""

    def __init__(self) -> None:
        self._cache: dict[str, Response] = {}
        self.network_fetches = 0

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        if url in self._cache:
            return self._cache[url]
        self.network_fetches += 1
        if url.endswith("missing.md"):
            response = Response(
                text="",
                headers={},
                status_code=404,
                status_text="Not Found",
                ok=False,
            )
        else:
            response = Response(
                text="ok",
                content=b"ok",
                headers={},
                status_code=200,
                status_text="OK",
                ok=True,
            )
        self._cache[url] = response
        return response


@pytest.fixture
def browser_scope(monkeypatch):
    monkeypatch.setattr("webcompy.ports._browser._resource.ENVIRONMENT", "pyscript")
    scope = DIScope()
    fetch_port = _CachingFetchPort()
    scope.provide(FETCH_PORT_KEY, fetch_port)
    scope.provide(RESOURCE_DATA_KEY, {})
    return scope, fetch_port


class TestPreloadServerNoop:
    @pytest.mark.asyncio
    async def test_server_preload_is_noop(self, tmp_path) -> None:
        (tmp_path / "a.md").write_text("# A", encoding="utf-8")
        port = ServerResourcePort(tmp_path, frozenset({"a.md"}))
        await port.preload(["a.md"])
        assert port.get_recorded_resources() == {}


class TestPreloadBrowser:
    @pytest.mark.asyncio
    async def test_preload_primes_cache_so_later_load_issues_no_fetch(self, browser_scope) -> None:
        scope, fetch_port = browser_scope
        port = BrowserResourcePort("/")
        with scope:
            await port.preload(["documents/a.md"])
            text = await port.load_text("documents/a.md")
        assert text == "ok"
        assert fetch_port.network_fetches == 1, "the load must be served from the primed cache"

    @pytest.mark.asyncio
    async def test_without_preload_load_fetches(self, browser_scope) -> None:
        scope, fetch_port = browser_scope
        port = BrowserResourcePort("/")
        with scope:
            await port.load_text("documents/a.md")
        assert fetch_port.network_fetches == 1

    @pytest.mark.asyncio
    async def test_preload_skips_payload_present_paths(self, browser_scope) -> None:
        scope, fetch_port = browser_scope
        scope.provide(RESOURCE_DATA_KEY, {"documents/a.md": "b2s="})
        port = BrowserResourcePort("/")
        with scope:
            await port.preload(["documents/a.md"])
            text = await port.load_text("documents/a.md")
        assert text == "ok"
        assert fetch_port.network_fetches == 0, "payload-present path must not be fetched"

    @pytest.mark.asyncio
    async def test_preload_failure_not_raised_but_load_raises(self, browser_scope) -> None:
        scope, _fetch_port = browser_scope
        port = BrowserResourcePort("/")
        with scope:
            await port.preload(["documents/missing.md"])
            with pytest.raises(ResourceNotFoundError):
                await port.load_text("documents/missing.md")
