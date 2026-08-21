from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass

import httpx
import pytest

from webcompy.ajax._sse import _SSEParser
from webcompy.rpc._registry import ProcedureRegistry
from webcompy_server.rpc import create_dispatcher_app


def _make_app(registry: ProcedureRegistry):
    return create_dispatcher_app(registry)


@dataclass
class Item:
    n: int


def _add(a: int, b: int = 0) -> int:
    return a + b


async def _count_up(n: int) -> AsyncIterator[int]:
    for i in range(1, n + 1):
        yield i


def _count_up_sync(n: int) -> Iterator[int]:
    yield from range(1, n + 1)


async def _items(n: int) -> AsyncIterator[Item]:
    for i in range(1, n + 1):
        yield Item(i)


async def _fail_midway() -> AsyncIterator[int]:
    yield 1
    raise RuntimeError("boom")


def _make_registry() -> ProcedureRegistry:
    registry = ProcedureRegistry()
    registry.register("add", _add)
    registry.register("count_up", _count_up)
    registry.register("count_up_sync", _count_up_sync)
    registry.register("items", _items)
    registry.register("fail_midway", _fail_midway)
    return registry


def _sse_events(text: str) -> list[tuple[str, str]]:
    parser = _SSEParser()
    events: list[tuple[str, str]] = []
    for event in parser.feed(text):
        events.append((event.event_type, event.data))
    return events


async def _post_stream(app, payload: object) -> tuple[int, dict[str, str], str]:
    async with (
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
        client.stream("POST", "/", json=payload) as response,
    ):
        status = response.status_code
        headers = dict(response.headers)
        body = (await response.aread()).decode("utf-8")
    return status, headers, body


async def _post_json(app, payload: object) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/", json=payload)


def _body_bytes(payload: object) -> bytes:
    return json.dumps(payload).encode("utf-8")


class TestHttpStreaming:
    @pytest.mark.asyncio
    async def test_successful_stream_emits_items_then_done(self) -> None:
        app = _make_app(_make_registry())

        status, headers, body = await _post_stream(
            app, {"jsonrpc": "2.0", "method": "count_up", "params": {"n": 2}, "id": 1, "stream": True}
        )

        assert status == 200
        assert headers["content-type"].startswith("text/event-stream")
        assert headers["cache-control"] == "no-store"
        events = _sse_events(body)
        assert [t for t, _ in events] == ["item", "item", "done"]
        assert json.loads(events[0][1]) == {"data": 1, "meta": None}
        assert json.loads(events[1][1]) == {"data": 2, "meta": None}

    @pytest.mark.asyncio
    async def test_sync_generator_streams_items(self) -> None:
        app = _make_app(_make_registry())

        status, _, body = await _post_stream(
            app, {"jsonrpc": "2.0", "method": "count_up_sync", "params": {"n": 3}, "id": 1, "stream": True}
        )

        assert status == 200
        events = _sse_events(body)
        assert [t for t, _ in events] == ["item", "item", "item", "done"]
        assert [json.loads(d)["data"] for _, d in events[:-1]] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_typed_items_encoded_with_meta(self) -> None:
        app = _make_app(_make_registry())

        _, _, body = await _post_stream(
            app, {"jsonrpc": "2.0", "method": "items", "params": {"n": 1}, "id": 1, "stream": True}
        )

        events = _sse_events(body)
        assert [t for t, _ in events] == ["item", "done"]
        item_event = json.loads(events[0][1])
        assert item_event["data"] == {"n": 1}

    @pytest.mark.asyncio
    async def test_mid_stream_exception_emits_error_without_done(self) -> None:
        app = _make_app(_make_registry())

        _, _, body = await _post_stream(app, {"jsonrpc": "2.0", "method": "fail_midway", "id": 1, "stream": True})

        events = _sse_events(body)
        assert [t for t, _ in events] == ["item", "error"]
        error_event = json.loads(events[1][1])
        assert error_event["code"] == -32603
        assert "boom" not in error_event["message"]

    @pytest.mark.asyncio
    async def test_invalid_params_answers_json_before_stream(self) -> None:
        app = _make_app(_make_registry())

        response = await _post_json(
            app, {"jsonrpc": "2.0", "method": "count_up", "params": {"n": "x"}, "id": 1, "stream": True}
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        assert response.json()["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_unknown_method_with_flag_answers_json(self) -> None:
        app = _make_app(_make_registry())

        response = await _post_json(app, {"jsonrpc": "2.0", "method": "missing", "id": 1, "stream": True})

        assert response.headers["content-type"].startswith("application/json")
        assert response.json()["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_streaming_procedure_without_member_answers_json_error(self) -> None:
        app = _make_app(_make_registry())

        response = await _post_json(app, {"jsonrpc": "2.0", "method": "count_up", "params": {"n": 1}, "id": 1})

        assert response.headers["content-type"].startswith("application/json")
        assert response.json()["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_ordinary_procedure_with_member_answers_json_error(self) -> None:
        app = _make_app(_make_registry())

        response = await _post_json(
            app, {"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2}, "id": 1, "stream": True}
        )

        assert response.headers["content-type"].startswith("application/json")
        assert response.json()["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_streaming_entry_in_batch_answers_error_per_entry(self) -> None:
        app = _make_app(_make_registry())

        response = await _post_json(
            app,
            [
                {"jsonrpc": "2.0", "method": "count_up", "params": {"n": 1}, "id": 1, "stream": True},
                {"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2}, "id": 2},
            ],
        )

        body = response.json()
        by_id = {entry["id"]: entry for entry in body}
        assert by_id[1]["error"]["code"] == -32600
        assert by_id[2]["result"] == 3

    @pytest.mark.asyncio
    async def test_notification_to_streaming_procedure_does_not_execute(self) -> None:
        recorded: list[int] = []

        async def _recording() -> AsyncIterator[int]:
            recorded.append(1)
            yield 1

        registry = ProcedureRegistry()
        registry.register("recording", _recording)
        app = _make_app(registry)

        response = await _post_json(app, {"jsonrpc": "2.0", "method": "recording"})

        assert response.status_code == 204
        assert response.content == b""
        assert recorded == []


class TestHttpStreamingDisconnect:
    @pytest.mark.asyncio
    async def test_client_disconnect_stops_and_closes_generator(self) -> None:
        closed: dict[str, bool] = {"closed": False}
        release = asyncio.Event()

        async def _blocking() -> AsyncIterator[int]:
            try:
                yield 1
                await release.wait()
                yield 2
            finally:
                closed["closed"] = True

        registry = ProcedureRegistry()
        registry.register("blocking", _blocking)
        app = _make_app(registry)

        messages = [
            {
                "type": "http.request",
                "body": _body_bytes({"jsonrpc": "2.0", "method": "blocking", "id": 1, "stream": True}),
                "more_body": False,
            },
            {"type": "http.disconnect"},
        ]

        async def _receive() -> dict[str, object]:
            return messages.pop(0)

        sent: list[dict[str, object]] = []

        async def _send(message: dict[str, object]) -> None:
            sent.append(message)

        scope: dict[str, object] = {"type": "http", "method": "POST"}

        await app(scope, _receive, _send)

        assert closed["closed"] is True
        sent_bodies = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")  # type: ignore[arg-type]
        assert b"event: item" in sent_bodies
        assert b"event: done" not in sent_bodies
        assert b"event: error" not in sent_bodies

    @pytest.mark.asyncio
    async def test_disconnect_during_sync_generator_closes_it(self) -> None:
        closed: dict[str, bool] = {"closed": False}

        def _blocking_sync() -> Iterator[int]:
            try:
                while True:
                    yield 1
            finally:
                closed["closed"] = True

        registry = ProcedureRegistry()
        registry.register("blocking_sync", _blocking_sync)
        app = _make_app(registry)

        messages = [
            {
                "type": "http.request",
                "body": _body_bytes({"jsonrpc": "2.0", "method": "blocking_sync", "id": 1, "stream": True}),
                "more_body": False,
            },
            {"type": "http.disconnect"},
        ]

        async def _receive() -> dict[str, object]:
            return messages.pop(0)

        sent: list[dict[str, object]] = []

        async def _send(message: dict[str, object]) -> None:
            sent.append(message)

        scope: dict[str, object] = {"type": "http", "method": "POST"}

        await app(scope, _receive, _send)

        assert closed["closed"] is True
