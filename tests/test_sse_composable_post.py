from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

import webcompy.realtime._sse as sse_mod
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.ports._fetch import FetchStream, Response
from webcompy.ports._keys import EVENT_SOURCE_PORT_KEY, FETCH_PORT_KEY
from webcompy.realtime import ConnectionState, SSEvent, use_event_source
from webcompy_testing import FakeEventSourcePort, FakeFetchPort


class _FakeFetchStream(FetchStream):
    def __init__(
        self,
        chunks: list[str],
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        ok: bool = True,
    ) -> None:
        super().__init__(status_code, headers or {"content-type": "text/event-stream"}, ok)
        self._chunks = iter(chunks)
        self.aborted = False

    async def __anext__(self) -> str:
        if self._closed:
            raise StopAsyncIteration
        try:
            return next(self._chunks)
        except StopIteration:
            raise StopAsyncIteration from None

    def close(self) -> None:
        if self._closed:
            return
        super().close()
        self.aborted = True


class _HangingFetchStream(FetchStream):
    def __init__(
        self,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        ok: bool = True,
    ) -> None:
        super().__init__(status_code, headers or {"content-type": "text/event-stream"}, ok)
        self._yielded = False
        self.aborted = False

    async def __anext__(self) -> str:
        if self._closed:
            raise StopAsyncIteration
        if not self._yielded:
            self._yielded = True
            return "data: m\n\n"
        await asyncio.sleep(3600)
        raise StopAsyncIteration

    def close(self) -> None:
        if self._closed:
            return
        super().close()
        self.aborted = True


class _StreamingFetchPort(FakeFetchPort):
    def __init__(
        self,
        streams: dict[tuple[str, str], list[str]] | None = None,
        responses: dict[tuple[str, str], Response] | None = None,
        stream_sequence: dict[tuple[str, str], list[list[str]]] | None = None,
    ) -> None:
        super().__init__(responses=responses, streams=streams)
        self._stream_sequence = stream_sequence or {}
        self._hanging: set[tuple[str, str]] = set()
        self._attempt_index: dict[tuple[str, str], int] = {}
        self.open_calls: list[tuple[str, str, dict[str, str] | None, str | None]] = []
        self.streams: list[FetchStream] = []

    async def stream(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> FetchStream:
        key = (method, url)
        self.open_calls.append((url, method, headers, body))
        if key in self._hanging:
            stream = _HangingFetchStream()
            self.streams.append(stream)
            return stream
        if key in self._stream_sequence:
            attempts = self._stream_sequence[key]
            index = min(self._attempt_index.get(key, 0), len(attempts) - 1)
            self._attempt_index[key] = index + 1
            stream = _FakeFetchStream(attempts[index])
            self.streams.append(stream)
            return stream
        stream = await super().stream(url, method=method, headers=headers, body=body)
        self.streams.append(stream)
        return stream


@pytest.fixture
def rt_env(monkeypatch):
    scope = DIScope()
    fetch_port = _StreamingFetchPort()
    es_port = FakeEventSourcePort()
    scope.provide(FETCH_PORT_KEY, fetch_port)
    scope.provide(EVENT_SOURCE_PORT_KEY, es_port)
    monkeypatch.setattr(sse_mod, "_get_app_di_scope", lambda: scope)
    token = _active_di_scope.set(scope)
    yield SimpleNamespace(scope=scope, port=fetch_port, es_port=es_port)
    _active_di_scope.reset(token)


async def _collect(handle: Any, limit: int | None = None) -> list[SSEvent]:
    out: list[SSEvent] = []
    async for ev in handle:
        out.append(ev)
        if limit is not None and len(out) >= limit:
            break
    return out


async def _settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


async def _wait_until(condition: Any, attempts: int = 100) -> None:
    for _ in range(attempts):
        if condition():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition not met within attempts")


class TestFetchTransport:
    @pytest.mark.asyncio
    async def test_post_request_sends_body_and_headers(self, rt_env) -> None:
        rt_env.port._streams[("POST", "/query")] = ["data: ok\n\n"]
        es = use_event_source("/query", method="POST", body='{"q":"x"}', headers={"Content-Type": "application/json"})
        await _settle()
        assert rt_env.port.open_calls == [("/query", "POST", {"Content-Type": "application/json"}, '{"q":"x"}')]
        got = await _collect(es, limit=1)
        assert got == [SSEvent(event="message", data="ok", last_event_id="")]
        es.close()

    @pytest.mark.asyncio
    async def test_named_events_are_delivered_with_last_event_id(self, rt_env) -> None:
        rt_env.port._streams[("POST", "/events")] = ["event: result\nid: 7\ndata: ok\n\n"]
        es = use_event_source("/events", method="POST", body="{}", events=("result",))
        got = await _collect(es, limit=1)
        assert got == [SSEvent(event="result", data="ok", last_event_id="7")]
        es.close()

    @pytest.mark.asyncio
    async def test_multiple_events_in_one_stream_are_delivered_in_order(self, rt_env) -> None:
        rt_env.port._streams[("POST", "/events")] = ["data: a\n\n", "data: b\n\n"]
        es = use_event_source("/events", method="POST", body="{}")
        got = await _collect(es, limit=2)
        assert [ev.data for ev in got] == ["a", "b"]
        es.close()

    @pytest.mark.asyncio
    async def test_non_successful_status_enters_reconnecting(self, rt_env, monkeypatch) -> None:
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_BASE_DELAY", 1000)
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_MAX_DELAY", 1000)
        rt_env.port._responses[("POST", "/events")] = Response(
            text="boom", headers={}, status_code=500, status_text="Error", ok=False
        )
        es = use_event_source("/events", method="POST", body="{}")
        await _wait_until(lambda: es.state.value == ConnectionState.RECONNECTING)
        es.close()

    @pytest.mark.asyncio
    async def test_non_sse_content_type_enters_reconnecting(self, rt_env, monkeypatch) -> None:
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_BASE_DELAY", 1000)
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_MAX_DELAY", 1000)
        rt_env.port._responses[("POST", "/events")] = Response(
            text="plain", headers={"content-type": "text/plain"}, status_code=200, status_text="OK", ok=True
        )
        es = use_event_source("/events", method="POST", body="{}")
        await _wait_until(lambda: es.state.value == ConnectionState.RECONNECTING)
        es.close()


class TestFetchFilteringAndSharing:
    @pytest.mark.asyncio
    async def test_per_subscriber_filtering_on_a_shared_connection(self, rt_env) -> None:
        rt_env.port._streams[("POST", "/events")] = ["event: a\ndata: 1\n\nevent: b\ndata: 2\n\n"]
        a = use_event_source("/events", method="POST", body="{}", events=("a",))
        b = use_event_source("/events", method="POST", body="{}", events=("b",))
        await _settle()
        assert len(rt_env.port.open_calls) == 1
        got_a = await _collect(a, limit=1)
        got_b = await _collect(b, limit=1)
        assert got_a == [SSEvent(event="a", data="1", last_event_id="")]
        assert got_b == [SSEvent(event="b", data="2", last_event_id="")]
        a.close()
        b.close()

    @pytest.mark.asyncio
    async def test_identical_post_requests_share_one_connection(self, rt_env) -> None:
        rt_env.port._streams[("POST", "/events")] = ["data: m\n\n"]
        a = use_event_source("/events", method="POST", body="x")
        b = use_event_source("/events", method="POST", body="x")
        await _settle()
        assert len(rt_env.port.open_calls) == 1
        got_a = await _collect(a, limit=1)
        got_b = await _collect(b, limit=1)
        assert got_a == got_b == [SSEvent(event="message", data="m", last_event_id="")]
        a.close()
        b.close()

    @pytest.mark.asyncio
    async def test_different_bodies_open_separate_connections(self, rt_env) -> None:
        rt_env.port._streams[("POST", "/events")] = ["data: m\n\n"]
        a = use_event_source("/events", method="POST", body="a")
        b = use_event_source("/events", method="POST", body="b")
        await _settle()
        assert len(rt_env.port.open_calls) == 2
        a.close()
        b.close()

    @pytest.mark.asyncio
    async def test_last_detach_closes_the_fetch_connection(self, rt_env) -> None:
        rt_env.port._hanging.add(("POST", "/events"))
        a = use_event_source("/events", method="POST", body="x")
        b = use_event_source("/events", method="POST", body="x")
        await _settle()
        assert len(rt_env.port.open_calls) == 1
        a.close()
        await _settle()
        assert len(rt_env.port.streams) == 1
        assert not rt_env.port.streams[0].aborted
        b.close()
        await _settle()
        assert rt_env.port.streams[0].aborted


class TestFetchSsr:
    def test_non_get_degrades_with_noop_fetch_port(self, monkeypatch) -> None:
        from webcompy_server.ports import ServerFetchPort

        scope = DIScope()
        opened: list[str] = []

        class _TrackingNoopFetchPort(ServerFetchPort):
            async def stream(
                self,
                url: str,
                *,
                method: str = "GET",
                headers: dict[str, str] | None = None,
                body: str | None = None,
            ) -> FetchStream:
                opened.append(url)
                return await super().stream(url, method=method, headers=headers, body=body)

        scope.provide(FETCH_PORT_KEY, _TrackingNoopFetchPort())
        scope.provide(EVENT_SOURCE_PORT_KEY, FakeEventSourcePort())
        monkeypatch.setattr(sse_mod, "_get_app_di_scope", lambda: scope)
        token = _active_di_scope.set(scope)
        try:
            with pytest.warns(UserWarning, match="outside the browser"):
                es = use_event_source("/query", method="POST", body="{}")
            assert es.state.value == ConnectionState.CLOSED
            got = asyncio.run(_collect(es))
            assert got == []
            assert opened == []
        finally:
            _active_di_scope.reset(token)

    def test_non_get_without_fetch_port_returns_empty_closed_handle(self, monkeypatch) -> None:
        scope = DIScope()
        monkeypatch.setattr(sse_mod, "_get_app_di_scope", lambda: scope)
        token = _active_di_scope.set(scope)
        try:
            with pytest.warns(UserWarning, match="no FetchPort"):
                es = use_event_source("/query", method="POST", body="{}")
            assert es.state.value == ConnectionState.CLOSED
            got = asyncio.run(_collect(es))
            assert got == []
        finally:
            _active_di_scope.reset(token)


class TestFetchValidation:
    def test_get_with_body_is_rejected_before_any_open(self, rt_env) -> None:
        with pytest.raises(ValueError, match="only valid with non-GET"):
            use_event_source("/events", body="x")
        assert rt_env.port.open_calls == []

    def test_get_with_headers_is_rejected_before_any_open(self, rt_env) -> None:
        with pytest.raises(ValueError, match="only valid with non-GET"):
            use_event_source("/events", headers={"X-Token": "t"})
        assert rt_env.port.open_calls == []

    def test_empty_method_is_rejected_before_any_open(self, rt_env) -> None:
        with pytest.raises(TypeError, match="non-empty string"):
            use_event_source("/events", method="")
        assert rt_env.port.open_calls == []

    def test_none_method_is_rejected_before_any_open(self, rt_env) -> None:
        with pytest.raises(TypeError, match="non-empty string"):
            use_event_source("/events", method=None)  # type: ignore[arg-type]
        assert rt_env.port.open_calls == []

    def test_non_string_method_is_rejected_before_any_open(self, rt_env) -> None:
        with pytest.raises(TypeError, match="non-empty string"):
            use_event_source("/events", method=123)  # type: ignore[arg-type]
        assert rt_env.port.open_calls == []

    def test_get_path_still_uses_the_event_source_port(self, rt_env) -> None:
        es = use_event_source("/events")
        assert rt_env.port.open_calls == []
        assert len(rt_env.es_port.open_calls) == 1
        es.close()

    @pytest.mark.asyncio
    async def test_no_scope_falls_back_to_a_private_fetch_connection(self, monkeypatch) -> None:
        scope = DIScope()
        fetch_port = _StreamingFetchPort(streams={("POST", "/events"): ["data: m\n\n"]})
        scope.provide(FETCH_PORT_KEY, fetch_port)
        scope.provide(EVENT_SOURCE_PORT_KEY, FakeEventSourcePort())
        monkeypatch.setattr(sse_mod, "_get_app_di_scope", lambda: None)
        token = _active_di_scope.set(scope)
        try:
            with pytest.warns(UserWarning, match="no app DI scope"):
                es = use_event_source("/events", method="POST", body="x")
            await _wait_until(lambda: len(fetch_port.open_calls) == 1)
            got = await _collect(es, limit=1)
            assert got == [SSEvent(event="message", data="m", last_event_id="")]
            es.close()
        finally:
            _active_di_scope.reset(token)


class TestFetchReconnection:
    @pytest.mark.asyncio
    async def test_body_stream_end_triggers_reconnect_then_open(self, rt_env, monkeypatch) -> None:
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_BASE_DELAY", 0.01)
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_MAX_DELAY", 0.01)
        rt_env.port._stream_sequence[("POST", "/events")] = [["data: a\n\n"], ["data: b\n\n"]]
        es = use_event_source("/events", method="POST", body="x")
        got = await _collect(es, limit=2)
        assert [ev.data for ev in got] == ["a", "b"]
        assert len(rt_env.port.open_calls) == 2
        es.close()

    @pytest.mark.asyncio
    async def test_reconnect_carries_the_last_event_id(self, rt_env, monkeypatch) -> None:
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_BASE_DELAY", 0.01)
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_MAX_DELAY", 0.01)
        rt_env.port._stream_sequence[("POST", "/events")] = [["id: 7\ndata: a\n\n"], ["data: b\n\n"]]
        es = use_event_source("/events", method="POST", body="x")
        await _collect(es, limit=2)
        _, _, headers, _ = rt_env.port.open_calls[1]
        assert headers is not None
        assert headers.get("Last-Event-ID") == "7"
        es.close()

    @pytest.mark.asyncio
    async def test_reconnect_headers_preserve_user_headers(self, rt_env, monkeypatch) -> None:
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_BASE_DELAY", 0.01)
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_MAX_DELAY", 0.01)
        rt_env.port._stream_sequence[("POST", "/events")] = [["data: a\n\n"], ["data: b\n\n"]]
        es = use_event_source("/events", method="POST", body="x", headers={"Content-Type": "application/json"})
        await _collect(es, limit=2)
        _, _, headers, _ = rt_env.port.open_calls[1]
        assert headers is not None
        assert headers.get("Content-Type") == "application/json"
        es.close()

    @pytest.mark.asyncio
    async def test_close_during_reconnecting_stops_the_loop(self, rt_env, monkeypatch) -> None:
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_BASE_DELAY", 1000)
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_MAX_DELAY", 1000)
        rt_env.port._stream_sequence[("POST", "/events")] = [["data: a\n\n"]]
        es = use_event_source("/events", method="POST", body="x")
        await _wait_until(lambda: es.state.value == ConnectionState.RECONNECTING)
        assert len(rt_env.port.open_calls) == 1
        es.close()
        await _settle()
        assert es.state.value == ConnectionState.CLOSED
        assert len(rt_env.port.open_calls) == 1

    @pytest.mark.asyncio
    async def test_close_mid_stream_stops_delivery_and_aborts(self, rt_env) -> None:
        rt_env.port._hanging.add(("POST", "/events"))
        es = use_event_source("/events", method="POST", body="x")
        got = await _collect(es, limit=1)
        assert got == [SSEvent(event="message", data="m", last_event_id="")]
        es.close()
        await _settle()
        assert es.state.value == ConnectionState.CLOSED
        assert rt_env.port.streams[0].aborted
        assert await _collect(es) == []

    @pytest.mark.asyncio
    async def test_unsuccessful_handshake_retries_until_closed(self, rt_env, monkeypatch) -> None:
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_BASE_DELAY", 0.01)
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_MAX_DELAY", 0.01)
        rt_env.port._responses[("POST", "/events")] = Response(
            text="boom", headers={}, status_code=500, status_text="Error", ok=False
        )
        es = use_event_source("/events", method="POST", body="x")
        await _wait_until(lambda: len(rt_env.port.open_calls) >= 2)
        es.close()
        assert es.state.value == ConnectionState.CLOSED


class TestFetchRegistryKeying:
    @pytest.mark.asyncio
    async def test_new_event_types_do_not_reopen_fetch_connection(self, rt_env) -> None:
        rt_env.port._streams[("POST", "/events")] = ["event: a\ndata: 1\n\nevent: b\ndata: 2\n\n"]
        a = use_event_source("/events", method="POST", body="x", events=("a",))
        b = use_event_source("/events", method="POST", body="x", events=("b",))
        await _settle()
        assert len(rt_env.port.open_calls) == 1
        got_a = await _collect(a, limit=1)
        got_b = await _collect(b, limit=1)
        assert got_a == [SSEvent(event="a", data="1", last_event_id="")]
        assert got_b == [SSEvent(event="b", data="2", last_event_id="")]
        a.close()
        b.close()

    @pytest.mark.asyncio
    async def test_fetch_connection_state_transitions_connecting_open_reconnecting(self, rt_env, monkeypatch) -> None:
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_BASE_DELAY", 1000)
        monkeypatch.setattr(sse_mod, "_FETCH_RECONNECT_MAX_DELAY", 1000)
        rt_env.port._streams[("POST", "/events")] = ["data: a\n\n"]
        es = use_event_source("/events", method="POST", body="x")
        await _wait_until(lambda: es.state.value == ConnectionState.RECONNECTING)
        es.close()
        assert es.state.value == ConnectionState.CLOSED

    @pytest.mark.asyncio
    async def test_different_headers_open_separate_connections(self, rt_env) -> None:
        rt_env.port._streams[("POST", "/events")] = ["data: m\n\n"]
        a = use_event_source("/events", method="POST", body="x", headers={"Authorization": "Bearer a"})
        b = use_event_source("/events", method="POST", body="x", headers={"Authorization": "Bearer b"})
        await _settle()
        assert len(rt_env.port.open_calls) == 2
        a.close()
        b.close()

    @pytest.mark.asyncio
    async def test_identical_headers_share_one_connection(self, rt_env) -> None:
        rt_env.port._streams[("POST", "/events")] = ["data: m\n\n"]
        a = use_event_source(
            "/events", method="POST", body="x", headers={"Content-Type": "application/json", "X-A": "1"}
        )
        b = use_event_source(
            "/events", method="POST", body="x", headers={"Content-Type": "application/json", "X-A": "1"}
        )
        await _settle()
        assert len(rt_env.port.open_calls) == 1
        got_a = await _collect(a, limit=1)
        got_b = await _collect(b, limit=1)
        assert got_a == got_b == [SSEvent(event="message", data="m", last_event_id="")]
        a.close()
        b.close()

    @pytest.mark.asyncio
    async def test_headers_key_normalizes_header_name_case(self, rt_env) -> None:
        rt_env.port._streams[("POST", "/events")] = ["data: m\n\n"]
        a = use_event_source("/events", method="POST", body="x", headers={"Content-Type": "application/json"})
        b = use_event_source("/events", method="POST", body="x", headers={"content-type": "application/json"})
        await _settle()
        assert len(rt_env.port.open_calls) == 1
        a.close()
        b.close()
