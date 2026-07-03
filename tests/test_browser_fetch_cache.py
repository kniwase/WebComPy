from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

import webcompy.ports._browser._fetch as _fetch_module
from webcompy.hydration._payload import TransferFetchEntry
from webcompy.ports._browser._fetch import BrowserFetchPort


@pytest.fixture(autouse=True)
def _patch_environment(monkeypatch, fake_browser):
    monkeypatch.setattr("webcompy.utils._environment.ENVIRONMENT", "pyscript")
    monkeypatch.setattr("webcompy.ports._browser._fetch.ENVIRONMENT", "pyscript")
    _fetch_module._raw_browser = fake_browser


class TestBrowserFetchCache:
    @pytest.mark.asyncio
    async def test_populate_from_transfer_creates_response_objects(self, fake_browser_full):
        port = BrowserFetchPort()
        entry = TransferFetchEntry(
            status_code=200,
            headers={"content-type": "text/plain"},
            body="cached body",
        )
        port.populate_from_transfer({"/api/data": entry})

        assert "/api/data" in port._response_cache
        cached = port._response_cache["/api/data"]
        assert cached.status_code == 200
        assert cached.text == "cached body"
        assert cached.headers["content-type"] == "text/plain"
        assert cached.ok is True

    @pytest.mark.asyncio
    async def test_fetch_returns_cached_response_without_network(self, fake_browser_full, monkeypatch):
        port = BrowserFetchPort()
        port._browser.fetch = AsyncMock()
        port._browser.fetch.return_value = MagicMock(
            text=AsyncMock(return_value="network response"),
            headers={},
            status=200,
            statusText="OK",
            ok=True,
        )

        entry = TransferFetchEntry(status_code=200, headers={}, body="cached response")
        port.populate_from_transfer({"/api/data": entry})

        response = await port.fetch("/api/data")
        assert response.text == "cached response"
        assert port._browser.fetch.await_count == 0

    @pytest.mark.asyncio
    async def test_fetch_makes_network_request_for_non_cached_urls(self, fake_browser_full):
        port = BrowserFetchPort()

        mock_response = MagicMock()
        mock_response.text = AsyncMock(return_value="from network")
        mock_response.headers = {"content-type": "application/json"}
        mock_response.status = 200
        mock_response.statusText = "OK"
        mock_response.ok = True
        port._browser.fetch = AsyncMock(return_value=mock_response)

        response = await port.fetch("/api/not-cached")
        assert response.text == "from network"
        port._browser.fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cache_persists_across_multiple_fetches(self, fake_browser_full):
        port = BrowserFetchPort()

        entry = TransferFetchEntry(status_code=200, headers={}, body="cached")
        port.populate_from_transfer({"/api/data": entry})

        response1 = await port.fetch("/api/data")
        response2 = await port.fetch("/api/data")
        assert response1.text == "cached"
        assert response2.text == "cached"
        assert response1 is response2

    @pytest.mark.asyncio
    async def test_cache_key_for_non_get_includes_method(self, fake_browser_full):
        port = BrowserFetchPort()

        key = port._cache_key("/api/data", "POST", '{"key":"val"}')
        assert "POST" in key
        assert "/api/data" in key
        assert '{"key":"val"}' in key

    @pytest.mark.asyncio
    async def test_cache_key_for_get_is_just_url(self, fake_browser_full):
        port = BrowserFetchPort()
        key = port._cache_key("/api/data", "GET")
        assert key == "/api/data"

    @pytest.mark.asyncio
    async def test_populate_from_transfer_updates_existing_cache(self, fake_browser_full):
        port = BrowserFetchPort()

        entry1 = TransferFetchEntry(status_code=200, headers={}, body="first")
        port.populate_from_transfer({"/api/data": entry1})
        assert port._response_cache["/api/data"].text == "first"

        entry2 = TransferFetchEntry(status_code=200, headers={}, body="second")
        port.populate_from_transfer({"/api/data": entry2})
        assert port._response_cache["/api/data"].text == "second"
