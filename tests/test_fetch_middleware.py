from __future__ import annotations

import asyncio
from typing import Any

import pytest

from webcompy.di import DIScope
from webcompy.exception import WebComPyException
from webcompy.ports._fetch import FetchPort, FetchStream, Response, _BufferedFetchStream
from webcompy.ports._keys import FETCH_MIDDLEWARE_KEY
from webcompy.ports._middleware import (
    FetchMiddleware,
    FetchMiddlewareRegistry,
    FetchRequest,
    _MiddlewareFetchPort,
    add_fetch_middleware,
)


def _response(text: str = "ok", status_code: int = 200) -> Response:
    return Response(
        text=text,
        headers={},
        status_code=status_code,
        status_text="OK",
        ok=status_code < 400,
    )


class _RecordingPort(FetchPort):
    def __init__(self, text: str = "ok") -> None:
        self.calls: list[dict[str, Any]] = []
        self._text = text

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        self.calls.append({"url": url, "method": method, "headers": headers, "body": body})
        return _response(self._text)


class _StreamRecordingPort(_RecordingPort):
    def __init__(self, text: str = "chunk") -> None:
        super().__init__(text)
        self.stream_calls: list[dict[str, Any]] = []

    async def stream(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> FetchStream:
        self.stream_calls.append({"url": url, "method": method, "headers": headers})
        return _BufferedFetchStream(200, {"x-from": "port"}, True, self._text)


def _tracking_middleware(
    name: str,
    log: list[str],
    *,
    intercept_url: str | None = None,
) -> FetchMiddleware:
    async def middleware(request: FetchRequest, next):  # type: ignore[name-defined]
        log.append(f"{name}>")
        if intercept_url is not None and request.url == intercept_url:
            log.append(f"{name}!")
            return _response(f"mocked-by-{name}")
        result = await next(request)
        log.append(f"<{name}")
        return result

    return middleware


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def test_no_middleware_delegates_unchanged() -> None:
    port = _RecordingPort()
    registry = FetchMiddlewareRegistry()
    wrapped = _MiddlewareFetchPort(port, registry)

    response = _run(wrapped.fetch("http://example.test/", headers={"a": "b"}))

    assert response.text == "ok"
    assert len(port.calls) == 1
    assert port.calls[0]["headers"] == {"a": "b"}
    assert wrapped.is_self_site_url("http://example.test/") is False


def test_bytes_body_passes_through_unchanged() -> None:
    port = _RecordingPort()
    registry = FetchMiddlewareRegistry()

    async def passthrough(request: FetchRequest, next):  # type: ignore[name-defined]
        return await next(request)

    registry.use(passthrough)
    body = b"\x89PNG\r\n\x1a\n-binary"
    _run(_MiddlewareFetchPort(port, registry).fetch("http://example.test/bin", method="POST", body=body))

    assert len(port.calls) == 1
    assert port.calls[0]["body"] == body


def test_middleware_mutates_request_before_next() -> None:
    port = _RecordingPort()
    registry = FetchMiddlewareRegistry()

    async def add_auth(request: FetchRequest, next):  # type: ignore[name-defined]
        headers = dict(request.headers or {})
        headers["Authorization"] = "Bearer token"
        request.headers = headers
        return await next(request)

    registry.use(add_auth)
    _run(_MiddlewareFetchPort(port, registry).fetch("http://example.test/", headers={}))

    assert port.calls[0]["headers"]["Authorization"] == "Bearer token"


def test_first_registered_is_outermost() -> None:
    port = _RecordingPort()
    log: list[str] = []
    registry = FetchMiddlewareRegistry()
    registry.use(_tracking_middleware("a", log))
    registry.use(_tracking_middleware("b", log))
    registry.use(_tracking_middleware("c", log))

    _run(_MiddlewareFetchPort(port, registry).fetch("http://example.test/"))

    assert log == ["a>", "b>", "c>", "<c", "<b", "<a"]


def test_intercept_by_returning_without_next() -> None:
    port = _RecordingPort()
    log: list[str] = []
    registry = FetchMiddlewareRegistry()
    registry.use(_tracking_middleware("outer", log))
    registry.use(_tracking_middleware("inner", log, intercept_url="http://example.test/mock"))
    wrapped = _MiddlewareFetchPort(port, registry)

    mocked = _run(wrapped.fetch("http://example.test/mock"))
    normal = _run(wrapped.fetch("http://example.test/plain"))

    assert mocked.text == "mocked-by-inner"
    assert normal.text == "ok"
    assert len(port.calls) == 1


def test_short_circuit_via_next_response_kwarg() -> None:
    port = _RecordingPort()
    seen: list[Any] = []
    registry = FetchMiddlewareRegistry()

    outer_calls: list[int] = []

    async def outer(request: FetchRequest, next):  # type: ignore[name-defined]
        outer_calls.append(1)
        synthetic = _response("short-circuit")
        result = await next(request, response=synthetic)
        seen.append(result)
        return result

    inner_called: list[int] = []

    async def inner(request: FetchRequest, next):  # type: ignore[name-defined]
        inner_called.append(1)
        return await next(request)

    registry.use(outer)
    registry.use(inner)
    result = _run(_MiddlewareFetchPort(port, registry).fetch("http://example.test/"))

    assert result.text == "short-circuit"
    assert seen == [result]
    assert inner_called == []
    assert port.calls == []


def test_stream_metadata_available_before_consumption() -> None:
    port = _StreamRecordingPort()
    observed: list[tuple[int, bool]] = []
    registry = FetchMiddlewareRegistry()

    async def inspect(request: FetchRequest, next):  # type: ignore[name-defined]
        stream = await next(request)
        observed.append((stream.status_code, stream.ok))
        chunks = [chunk async for chunk in stream]
        observed.append((len(chunks), -1))
        return stream

    registry.use(inspect)
    stream_result = _run(_MiddlewareFetchPort(port, registry).stream("http://example.test/s"))

    assert observed == [(200, True), (1, -1)]
    assert stream_result.headers == {"x-from": "port"}
    assert len(port.stream_calls) == 1
    assert port.calls == []


def test_stream_short_circuit_with_synthetic_stream() -> None:
    port = _StreamRecordingPort()
    registry = FetchMiddlewareRegistry()

    async def mock_stream(request: FetchRequest, next):  # type: ignore[name-defined]
        return await next(request, response=_BufferedFetchStream(200, {}, True, "synthetic"))

    registry.use(mock_stream)
    stream = _run(_MiddlewareFetchPort(port, registry).stream("http://example.test/s"))

    async def consume():
        return [chunk async for chunk in stream]

    assert "".join(_run(consume())) == "synthetic"
    assert port.stream_calls == []


def test_generation_rebuild_applies_late_registration() -> None:
    port = _RecordingPort()
    registry = FetchMiddlewareRegistry()
    wrapped = _MiddlewareFetchPort(port, registry)

    first = _run(wrapped.fetch("http://example.test/"))
    assert first.headers == {}

    late_log: list[str] = []
    registry.use(_tracking_middleware("late", late_log))
    _run(wrapped.fetch("http://example.test/"))

    assert late_log == ["late>", "<late"]


def test_registry_snapshot_is_immutable_view() -> None:
    registry = FetchMiddlewareRegistry()

    async def mw(request: FetchRequest, next):  # type: ignore[name-defined]
        return await next(request)

    registry.use(mw)
    snapshot = registry.middlewares
    registry.use(mw)

    assert len(snapshot) == 1
    assert len(registry.middlewares) == 2


def test_delegation_populate_from_transfer_and_noop() -> None:
    seeded: list[Any] = []

    class _HydrationPort(FetchPort):
        noop = True

        def populate_from_transfer(self, data: dict[str, Any]) -> None:
            seeded.append(data)

        async def fetch(
            self,
            url: str,
            *,
            method: str = "GET",
            headers: dict[str, str] | None = None,
            body: str | None = None,
        ) -> Response:
            raise WebComPyException("not used")

    wrapped = _MiddlewareFetchPort(_HydrationPort(), FetchMiddlewareRegistry())

    assert wrapped.noop is True
    wrapped.populate_from_transfer({"GET /x": {}})
    assert seeded == [{"GET /x": {}}]


def test_fetch_head_rebuilt_only_on_generation_change() -> None:
    port = _RecordingPort()
    registry = FetchMiddlewareRegistry()
    wrapped = _MiddlewareFetchPort(port, registry)

    wrapped._ensure_chains()
    first_head = wrapped._fetch_head
    wrapped._ensure_chains()
    assert wrapped._fetch_head is first_head

    async def noop_mw(request: FetchRequest, next):  # type: ignore[name-defined]
        return await next(request)

    registry.use(noop_mw)
    wrapped._ensure_chains()
    assert wrapped._fetch_head is not first_head


def test_add_fetch_middleware_registers_in_active_scope() -> None:
    registry = FetchMiddlewareRegistry()
    scope = DIScope()
    scope.__enter__()
    try:
        scope.provide(FETCH_MIDDLEWARE_KEY, registry)

        async def mw(request: FetchRequest, next):  # type: ignore[name-defined]
            return await next(request)

        add_fetch_middleware(mw)
        assert registry.middlewares == (mw,)
    finally:
        scope.__exit__(None, None, None)


def test_add_fetch_middleware_without_scope_raises() -> None:
    async def mw(request: FetchRequest, next):  # type: ignore[name-defined]
        return await next(request)

    with pytest.raises(RuntimeError, match="No active fetch middleware registry"):
        add_fetch_middleware(mw)
