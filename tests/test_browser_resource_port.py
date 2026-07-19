from __future__ import annotations

import base64
from typing import Any

import pytest

from webcompy.di._keys import RESOURCE_DATA_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.exception import WebComPyException
from webcompy.ports import ResourceNotFoundError
from webcompy.ports._browser._resource import BrowserResourcePort
from webcompy.ports._fetch import Response
from webcompy.ports._keys import FETCH_PORT_KEY


@pytest.fixture(autouse=True)
def _patch_environment(monkeypatch):
    monkeypatch.setattr("webcompy.utils._environment.ENVIRONMENT", "pyscript")
    monkeypatch.setattr("webcompy.ports._browser._resource.ENVIRONMENT", "pyscript")


def _make_response(
    text: str,
    status_code: int = 200,
    ok: bool | None = None,
) -> Response:
    return Response(
        text=text,
        headers={"content-type": "text/plain"},
        status_code=status_code,
        status_text="OK" if status_code < 400 else "Error",
        ok=ok if ok is not None else status_code < 400,
    )


class FakeFetchPort:
    """Simple test double for ``FetchPort``."""

    def __init__(
        self,
        response: Response | None = None,
        side_effect: BaseException | None = None,
    ) -> None:
        self.response = response
        self.side_effect = side_effect
        self.calls: list[Any] = []

    async def fetch(self, url: str, **_kwargs: Any) -> Response:
        self.calls.append(url)
        if self.side_effect is not None:
            raise self.side_effect
        assert self.response is not None
        return self.response


@pytest.fixture
def scope_with_payload():
    scope = DIScope()
    encoded = base64.b64encode(b"hello world").decode("ascii")
    scope.provide(RESOURCE_DATA_KEY, {"a.html": encoded})
    token = _active_di_scope.set(scope)
    yield scope
    _active_di_scope.reset(token)


@pytest.fixture
def scope_with_fake_fetch():
    scope = DIScope()
    scope.provide(RESOURCE_DATA_KEY, {})
    fetch_port = FakeFetchPort(response=_make_response("from network"))
    scope.provide(FETCH_PORT_KEY, fetch_port)
    token = _active_di_scope.set(scope)
    yield scope, fetch_port
    _active_di_scope.reset(token)


@pytest.fixture
def scope_with_empty_fetch():
    """Scope with RESOURCE_DATA_KEY but no FetchPort."""
    scope = DIScope()
    scope.provide(RESOURCE_DATA_KEY, {})
    token = _active_di_scope.set(scope)
    yield scope
    _active_di_scope.reset(token)


class TestBrowserResourcePortEnvironment:
    def test_raises_when_not_pyscript(self, monkeypatch):
        monkeypatch.setattr("webcompy.ports._browser._resource.ENVIRONMENT", "node")
        with pytest.raises(WebComPyException, match="browser environment"):
            BrowserResourcePort(base_url="/")

    def test_constructed_when_pyscript(self):
        port = BrowserResourcePort(base_url="/")
        assert port is not None


class TestBrowserResourcePortPayloadLookup:
    @pytest.mark.asyncio
    async def test_load_text_from_payload(self, scope_with_payload):
        port = BrowserResourcePort(base_url="/")
        text = await port.load_text("a.html")
        assert text == "hello world"

    @pytest.mark.asyncio
    async def test_load_bytes_from_payload(self, scope_with_payload):
        port = BrowserResourcePort(base_url="/")
        content = await port.load_bytes("a.html")
        assert content == b"hello world"


class TestBrowserResourcePortFetchFallback:
    @pytest.mark.asyncio
    async def test_fetch_triggered_for_payload_miss(self, scope_with_fake_fetch):
        _, fetch_port = scope_with_fake_fetch
        port = BrowserResourcePort(base_url="/")
        text = await port.load_text("late.html")
        assert text == "from network"
        assert len(fetch_port.calls) == 1
        assert fetch_port.calls[0] == "/_webcompy-resource/late.html"

    @pytest.mark.asyncio
    async def test_fetch_url_uses_configured_base_url(self, scope_with_fake_fetch):
        _, fetch_port = scope_with_fake_fetch
        port = BrowserResourcePort(base_url="/myapp")
        await port.load_text("late.html")
        assert fetch_port.calls[0] == "/myapp/_webcompy-resource/late.html"

    @pytest.mark.asyncio
    async def test_base_url_strips_trailing_slash(self, scope_with_fake_fetch):
        _, fetch_port = scope_with_fake_fetch
        port = BrowserResourcePort(base_url="/myapp/")
        await port.load_text("late.html")
        url = fetch_port.calls[0]
        assert url == "/myapp/_webcompy-resource/late.html"
        # No double slash between base_url and the prefix
        assert "//" not in url.replace("://", "")

    @pytest.mark.asyncio
    async def test_load_bytes_via_fetch_encodes_text_response(self, scope_with_fake_fetch):
        _ = scope_with_fake_fetch
        port = BrowserResourcePort(base_url="/")
        content = await port.load_bytes("late.html")
        assert content == b"from network"


class TestBrowserResourcePortFetchFailures:
    @pytest.mark.asyncio
    async def test_404_raises_resource_not_found(self):
        scope = DIScope()
        scope.provide(RESOURCE_DATA_KEY, {})
        fetch_port = FakeFetchPort(response=_make_response("Not Found", status_code=404, ok=False))
        scope.provide(FETCH_PORT_KEY, fetch_port)
        token = _active_di_scope.set(scope)
        try:
            port = BrowserResourcePort(base_url="/")
            with pytest.raises(ResourceNotFoundError, match=r"late\.html"):
                await port.load_text("late.html")
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_error_message_mentions_payload_miss_and_fetch(self):
        scope = DIScope()
        scope.provide(RESOURCE_DATA_KEY, {})
        fetch_port = FakeFetchPort(response=_make_response("Not Found", status_code=404, ok=False))
        scope.provide(FETCH_PORT_KEY, fetch_port)
        token = _active_di_scope.set(scope)
        try:
            port = BrowserResourcePort(base_url="/")
            with pytest.raises(ResourceNotFoundError) as excinfo:
                await port.load_text("late.html")
            message = str(excinfo.value)
            assert "payload miss" in message
            assert "fetch" in message.lower()
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_fetch_exception_raises_resource_not_found(self):
        scope = DIScope()
        scope.provide(RESOURCE_DATA_KEY, {})
        fetch_port = FakeFetchPort(side_effect=Exception("network down"))
        scope.provide(FETCH_PORT_KEY, fetch_port)
        token = _active_di_scope.set(scope)
        try:
            port = BrowserResourcePort(base_url="/")
            with pytest.raises(ResourceNotFoundError):
                await port.load_text("late.html")
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_missing_fetch_port_raises(self, scope_with_empty_fetch):
        _ = scope_with_empty_fetch
        port = BrowserResourcePort(base_url="/")
        with pytest.raises(ResourceNotFoundError):
            await port.load_text("late.html")
