from __future__ import annotations

import asyncio
import json
import time
import warnings
from collections.abc import AsyncIterator, Mapping
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from webcompy.aio._aio import aio_run
from webcompy.ajax._serde import from_json
from webcompy.di import inject
from webcompy.hydration._transfer_meta import apply_transfer_meta, encode_with_meta
from webcompy.ports._keys import WEBSOCKET_PORT_KEY
from webcompy.realtime import ConnectionState, use_websocket
from webcompy.rpc._client import _encode_params, _registry_or_error, _resolve_single
from webcompy.rpc._errors import SERVER_ERROR, RpcError
from webcompy.rpc._stream import (
    STREAM_CANCEL_METHOD,
    STREAM_DONE_METHOD,
    STREAM_ERROR_METHOD,
    RpcStream,
    _decode_stream_item,
)
from webcompy.signal import Signal
from webcompy.utils._environment import ENVIRONMENT

if TYPE_CHECKING:
    from webcompy.realtime import WebSocketHandle

E = TypeVar("E")

SUBSCRIBE_METHOD = "_webcompy.subscribe"
UNSUBSCRIBE_METHOD = "_webcompy.unsubscribe"
EVENT_METHOD = "_webcompy.event"
PING_METHOD = "_webcompy.ping"
PONG_METHOD = "_webcompy.pong"

_STOP: Any = object()

_SSR_MSG = "webcompy rpc: RpcWsClient used outside the browser; performing no socket work"
_CLOSED_MSG = "webcompy rpc: RpcWsClient is closed"


class RpcSubscriptionState(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    RESYNC_REQUIRED = "resync_required"
    CLOSED = "closed"


class RpcSubscription(Generic[E]):
    """An async iterator of server events for one subscription.

    ``.state`` is a ``Signal[RpcSubscriptionState]``: ``PENDING`` until the
    server confirms, ``ACTIVE`` while events flow, ``RESYNC_REQUIRED`` when the
    server reports the replay buffer overflowed (the caller should refetch
    authoritative state and resubscribe), and ``CLOSED`` after unsubscribe or
    close. ``.last_cursor`` is a ``Signal[int | None]`` tracking the last
    received cursor, used for automatic rejoin after reconnects.
    """

    def __init__(
        self,
        client: RpcWsClient,
        method: str,
        params: Any,
        event_type: type[E] | None,
        *,
        closed: bool = False,
    ) -> None:
        self._client = client
        self._method = method
        self._params = params
        self._event_type = event_type
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._sub_id: str | None = None
        self._done = closed
        self.state: Signal[RpcSubscriptionState] = Signal(
            RpcSubscriptionState.CLOSED if closed else RpcSubscriptionState.PENDING
        )
        self.last_cursor: Signal[int | None] = Signal(None)
        if closed:
            self._queue.put_nowait(_STOP)

    def __aiter__(self) -> AsyncIterator[E]:
        return self

    async def __anext__(self) -> E:
        if self._done:
            raise StopAsyncIteration
        item = await self._queue.get()
        if item is _STOP:
            self._done = True
            raise StopAsyncIteration
        return item

    def _deliver(self, params: Any) -> None:
        if self._done:
            return
        data = params.get("data")
        meta = params.get("meta")
        if meta is not None:
            if not isinstance(meta, Mapping):
                self._client._set_last_error(RpcError(SERVER_ERROR, "Malformed event meta"))
                return
            try:
                data = apply_transfer_meta(data, meta, strict=True, decoders=self._client._registry.meta_decoders)
            except ValueError as err:
                self._client._set_last_error(RpcError(SERVER_ERROR, f"Failed to apply event meta: {err}"))
                return
        if self._event_type is not None:
            try:
                data = from_json(self._event_type, data, strict=True)
            except (TypeError, ValueError) as err:
                self._client._set_last_error(RpcError(SERVER_ERROR, f"RPC event does not match schema: {err}"))
                return
        cursor = params.get("cursor")
        if isinstance(cursor, int):
            self.last_cursor.value = cursor
        self._queue.put_nowait(data)

    def _finish(self, state: RpcSubscriptionState) -> None:
        self._done = True
        self.state.value = state
        self._queue.put_nowait(_STOP)

    def close(self) -> None:
        if self._done:
            return
        self._done = True
        self.state.value = RpcSubscriptionState.CLOSED
        self._client._detach_subscription(self)
        self._queue.put_nowait(_STOP)


class RpcWsClient:
    """JSON-RPC 2.0 over a shared, auto-reconnecting WebSocket.

    Calls correlate responses by ``id`` and raise ``RpcError`` on error or
    disconnect (never silently retried). ``subscribe`` returns an
    ``RpcSubscription`` async iterator that automatically rejoins with the
    last received cursor after reconnects. Optional application-level heartbeat
    detects dead connections and forces an abnormal close so the reconnect
    loop engages. Browser-runtime only: outside the browser a warning is
    emitted and no socket work is performed.

    Create the client inside component setup so its subscriptions and the
    shared socket are released automatically on component destroy. When the
    client is held outside a component (e.g. a module-level service), call
    ``close()`` explicitly to release the connection.
    """

    def __init__(
        self,
        url: str | None = None,
        *,
        heartbeat_interval: float | None = 30.0,
        heartbeat_timeout: float = 10.0,
        reconnect_base_delay: float = 1.0,
        reconnect_max_delay: float = 30.0,
        reconnect_max_attempts: int | None = None,
        max_queue: int | None = None,
    ) -> None:
        self._registry = _registry_or_error()
        self._url = url or self._registry.endpoint_url
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_timeout = heartbeat_timeout
        self._in_flight: dict[Any, asyncio.Future[Any]] = {}
        self._pending_subscribe_calls: dict[Any, RpcSubscription[Any]] = {}
        self._subscriptions: dict[str, RpcSubscription[Any]] = {}
        self._streams: dict[str, RpcStream[Any]] = {}
        self._pending_stream_calls: dict[Any, tuple[RpcStream[Any], dict[str, str]]] = {}
        self._pending_subs: set[RpcSubscription[Any]] = set()
        self._closed = False
        self._last_frame_time = time.monotonic()
        self._last_error: Signal[Exception | None] = Signal(None)
        self._handle: WebSocketHandle | None = None
        self._closed_state: Signal[ConnectionState] = Signal(ConnectionState.CLOSED)
        port = inject(WEBSOCKET_PORT_KEY, default=None)
        if port is None or (ENVIRONMENT != "pyscript" and getattr(port, "noop", False)):
            warnings.warn(_SSR_MSG, UserWarning, stacklevel=2)
            self._ssr = True
            return
        self._ssr = False
        self._handle = use_websocket(
            self._url,
            reconnect_base_delay=reconnect_base_delay,
            reconnect_max_delay=reconnect_max_delay,
            reconnect_max_attempts=reconnect_max_attempts,
            max_queue=max_queue,
        )
        self._handle.state.on_after_updating(self._on_state_change)
        aio_run(self._reader())
        if heartbeat_interval is not None:
            aio_run(self._heartbeat_loop())
        from webcompy.components._hooks import _register_before_destroy_chained

        _register_before_destroy_chained(self.close)

    @property
    def state(self) -> Signal[ConnectionState]:
        if self._handle is None:
            return self._closed_state
        return self._handle.state

    @property
    def last_error(self) -> Signal[Exception | None]:
        return self._last_error

    def _set_last_error(self, error: Exception | None) -> None:
        self._last_error.value = error

    def _check_usable(self) -> WebSocketHandle:
        if self._ssr:
            raise RpcError(SERVER_ERROR, "RpcWsClient is not available outside the browser")
        if self._closed or self._handle is None:
            raise RpcError(SERVER_ERROR, _CLOSED_MSG)
        return self._handle

    async def call(self, method: str, params: Any = None, *, result_type: Any = None) -> Any:
        handle = self._check_usable()
        if handle.state.value != ConnectionState.OPEN:
            raise RpcError(SERVER_ERROR, "RPC WebSocket connection is not open")
        req_id = self._registry.next_id()
        envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "id": req_id}
        if params is not None:
            _encode_params(self._registry, envelope, params)
        future: asyncio.Future[Any] = asyncio.Future()
        self._in_flight[req_id] = future
        handle.send(json.dumps(envelope))
        try:
            data = await future
        finally:
            self._in_flight.pop(req_id, None)
        return _resolve_single(data, result_type, self._registry)

    async def notify(self, method: str, params: Any = None) -> None:
        handle = self._check_usable()
        if handle.state.value != ConnectionState.OPEN:
            raise RpcError(SERVER_ERROR, "RPC WebSocket connection is not open")
        envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            _encode_params(self._registry, envelope, params)
        handle.send(json.dumps(envelope))

    async def stream(self, method: str, params: Any = None, *, result_type: Any = None) -> RpcStream[Any]:
        if self._ssr:
            return RpcStream(closed=True)
        handle = self._check_usable()
        if handle.state.value != ConnectionState.OPEN:
            raise RpcError(SERVER_ERROR, "RPC WebSocket connection is not open")
        req_id = self._registry.next_id()
        envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "id": req_id, "stream": True}
        if params is not None:
            _encode_params(self._registry, envelope, params)
        holder: dict[str, str] = {}

        def _cancel() -> None:
            self._cancel_pending_stream(holder, req_id)

        rpc_stream: RpcStream[Any] = RpcStream(
            cancel=_cancel,
            decode=lambda data, meta: _decode_stream_item(data, meta, result_type, self._registry),
        )
        self._pending_stream_calls[req_id] = (rpc_stream, holder)
        handle.send(json.dumps(envelope))
        return rpc_stream

    def _cancel_pending_stream(self, holder: dict[str, str], req_id: Any) -> None:
        stream_id = holder.get("id")
        if stream_id is None:
            return
        self._pending_stream_calls.pop(req_id, None)
        self._send_stream_cancel(stream_id)

    def _handle_stream_ack(self, rpc_stream: RpcStream[Any], holder: dict[str, str], frame: Any) -> None:
        if "error" in frame:
            rpc_stream._fail(self._stream_ack_error(frame))
            return
        result = frame.get("result")
        stream_id = result.get("stream_id") if isinstance(result, dict) else None
        if not isinstance(stream_id, str):
            rpc_stream._fail(RpcError(SERVER_ERROR, "Malformed RPC stream response"))
            return
        if rpc_stream._finished:
            self._send_stream_cancel(stream_id)
            return
        holder["id"] = stream_id
        self._streams[stream_id] = rpc_stream

    def _stream_ack_error(self, frame: Any) -> RpcError:
        error = frame.get("error")
        if isinstance(error, dict) and isinstance(error.get("code"), int) and isinstance(error.get("message"), str):
            return RpcError(error["code"], error["message"], error.get("data"))
        return RpcError(SERVER_ERROR, "Malformed RPC stream response")

    def _send_stream_cancel(self, stream_id: str) -> None:
        self._streams.pop(stream_id, None)
        if self._closed or self._handle is None:
            return
        if self._handle.state.value != ConnectionState.OPEN:
            return
        envelope: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": STREAM_CANCEL_METHOD,
            "params": {"stream_id": stream_id},
        }
        self._handle.send(json.dumps(envelope))

    def subscribe(
        self,
        method: str,
        params: Any = None,
        *,
        event_type: type[E] | None = None,
    ) -> RpcSubscription[E]:
        if self._ssr:
            return RpcSubscription(self, method, params, event_type, closed=True)
        if self._closed or self._handle is None or self._handle.state.value == ConnectionState.CLOSED:
            return RpcSubscription(self, method, params, event_type, closed=True)
        sub = RpcSubscription(self, method, params, event_type)
        self._pending_subs.add(sub)
        if self._handle.state.value == ConnectionState.OPEN:
            self._send_subscribe(sub)
        from webcompy.components._hooks import _register_before_destroy_chained

        _register_before_destroy_chained(sub.close)
        return sub

    def _send_subscribe(self, sub: RpcSubscription[Any]) -> None:
        if self._closed or self._handle is None:
            return
        req_id = self._registry.next_id()
        json_params, meta = encode_with_meta(sub._params, type_handlers=self._registry.meta_encoders)
        inner: dict[str, Any] = {"method": sub._method, "params": json_params}
        if meta:
            inner["meta"] = meta
        if sub._sub_id is not None:
            inner["last_cursor"] = sub.last_cursor.value if sub.last_cursor.value is not None else 0
        envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": SUBSCRIBE_METHOD, "params": inner, "id": req_id}
        self._pending_subscribe_calls[req_id] = sub
        self._handle.send(json.dumps(envelope))

    def _send_unsubscribe(self, sub: RpcSubscription[Any]) -> None:
        if self._closed or self._handle is None:
            return
        if self._handle.state.value != ConnectionState.OPEN:
            return
        if sub._sub_id is None:
            return
        envelope: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": UNSUBSCRIBE_METHOD,
            "params": {"subscription_id": sub._sub_id},
        }
        self._handle.send(json.dumps(envelope))

    def _detach_subscription(self, sub: RpcSubscription[Any]) -> None:
        self._pending_subs.discard(sub)
        sub_id = sub._sub_id
        if sub_id is not None:
            self._subscriptions.pop(sub_id, None)
            if not self._closed:
                self._send_unsubscribe(sub)

    def _fail_subscribe(self, sub: RpcSubscription[Any], state: RpcSubscriptionState) -> None:
        """Finish a subscription whose subscribe/rejoin response failed.

        The subscription is removed from both tracking maps so a finished
        subscription is never re-subscribed on a later reconnect.
        """
        self._pending_subs.discard(sub)
        sub_id = sub._sub_id
        if sub_id is not None:
            self._subscriptions.pop(sub_id, None)
            sub._sub_id = None
        sub._finish(state)

    def _handle_subscribe_response(self, sub: RpcSubscription[Any], frame: Any) -> None:
        if sub._done:
            return
        if "error" in frame:
            self._fail_subscribe(sub, RpcSubscriptionState.CLOSED)
            return
        result = frame.get("result")
        if not isinstance(result, dict):
            self._fail_subscribe(sub, RpcSubscriptionState.CLOSED)
            return
        if result.get("resync_required"):
            self._fail_subscribe(sub, RpcSubscriptionState.RESYNC_REQUIRED)
            return
        sub_id = result.get("subscription_id")
        if not isinstance(sub_id, str):
            self._fail_subscribe(sub, RpcSubscriptionState.CLOSED)
            return
        old_id = sub._sub_id
        if old_id is not None:
            self._subscriptions.pop(old_id, None)
        self._subscriptions[sub_id] = sub
        sub._sub_id = sub_id
        self._pending_subs.discard(sub)
        sub.state.value = RpcSubscriptionState.ACTIVE

    def _on_state_change(self, state: ConnectionState) -> None:
        if self._closed:
            return
        if state == ConnectionState.OPEN:
            self._last_frame_time = time.monotonic()
            for sub in list(self._pending_subs):
                self._send_subscribe(sub)
            for sub in list(self._subscriptions.values()):
                self._send_subscribe(sub)
        elif state == ConnectionState.RECONNECTING:
            self._fail_in_flight()
            self._fail_streams()
        elif state == ConnectionState.CLOSED:
            self._fail_in_flight()
            self._fail_streams()
            for sub in list(self._pending_subs):
                self._pending_subs.discard(sub)
                sub._finish(RpcSubscriptionState.CLOSED)
            for sub in list(self._subscriptions.values()):
                sub._finish(RpcSubscriptionState.CLOSED)
            self._subscriptions.clear()

    def _fail_in_flight(self) -> None:
        futures = list(self._in_flight.values())
        self._in_flight.clear()
        self._pending_subscribe_calls.clear()
        pending_streams = list(self._pending_stream_calls.values())
        self._pending_stream_calls.clear()
        for fut in futures:
            if not fut.done():
                fut.set_exception(RpcError(SERVER_ERROR, "RPC WebSocket connection lost"))
        for rpc_stream, _holder in pending_streams:
            rpc_stream._fail(RpcError(SERVER_ERROR, "RPC WebSocket connection lost"))

    def _fail_streams(self) -> None:
        streams = list(self._streams.values())
        self._streams.clear()
        for stream in streams:
            stream._fail(RpcError(SERVER_ERROR, "RPC WebSocket connection lost"))

    async def _reader(self) -> None:
        if self._handle is None:
            return
        try:
            async for frame_text in self._handle:
                self._last_frame_time = time.monotonic()
                try:
                    frame = json.loads(frame_text)
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                    self._set_last_error(RpcError(SERVER_ERROR, "Malformed JSON-RPC WebSocket frame"))
                    continue
                if not isinstance(frame, dict):
                    continue
                method = frame.get("method")
                if method == EVENT_METHOD:
                    self._handle_event(frame)
                    continue
                if method == STREAM_DONE_METHOD:
                    self._handle_stream_done(frame)
                    continue
                if method == STREAM_ERROR_METHOD:
                    self._handle_stream_error(frame)
                    continue
                if method == PONG_METHOD:
                    continue
                req_id = frame.get("id")
                sub = self._pending_subscribe_calls.pop(req_id, None)
                if sub is not None:
                    self._handle_subscribe_response(sub, frame)
                    continue
                pending = self._pending_stream_calls.pop(req_id, None)
                if pending is not None:
                    self._handle_stream_ack(pending[0], pending[1], frame)
                    continue
                future = self._in_flight.pop(req_id, None)
                if future is not None:
                    future.set_result(frame)
        except StopAsyncIteration:
            pass
        finally:
            self._fail_in_flight()

    def _handle_event(self, frame: Any) -> None:
        params = frame.get("params")
        if not isinstance(params, dict):
            self._set_last_error(RpcError(SERVER_ERROR, "Malformed RPC event frame"))
            return
        stream_id = params.get("stream_id")
        if isinstance(stream_id, str):
            stream = self._streams.get(stream_id)
            if stream is not None:
                stream._deliver_raw(params.get("data"), params.get("meta"))
            return
        sub_id = params.get("subscription_id")
        if not isinstance(sub_id, str):
            return
        sub = self._subscriptions.get(sub_id)
        if sub is None:
            return
        sub._deliver(params)

    def _handle_stream_done(self, frame: Any) -> None:
        params = frame.get("params")
        if not isinstance(params, dict):
            return
        stream_id = params.get("stream_id")
        if not isinstance(stream_id, str):
            return
        stream = self._streams.pop(stream_id, None)
        if stream is not None:
            stream._finish()

    def _handle_stream_error(self, frame: Any) -> None:
        params = frame.get("params")
        if not isinstance(params, dict):
            return
        stream_id = params.get("stream_id")
        if not isinstance(stream_id, str):
            return
        code = params.get("code")
        message = params.get("message")
        if not isinstance(code, int) or not isinstance(message, str):
            stream = self._streams.pop(stream_id, None)
            if stream is not None:
                stream._fail(RpcError(SERVER_ERROR, "Malformed RPC stream error frame"))
            return
        stream = self._streams.pop(stream_id, None)
        if stream is not None:
            stream._fail(RpcError(code, message, params.get("data")))

    async def _heartbeat_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval or 0.0)
                if self._closed or self._handle is None:
                    return
                if self._handle.state.value != ConnectionState.OPEN:
                    continue
                self._handle.send(json.dumps({"jsonrpc": "2.0", "method": PING_METHOD, "params": {}}))
                await asyncio.sleep(self._heartbeat_timeout)
                if self._closed:
                    return
                if time.monotonic() - self._last_frame_time >= self._heartbeat_timeout and (
                    self._handle.state.value == ConnectionState.OPEN
                ):
                    self._handle.force_close(4000, "heartbeat timeout")
        except asyncio.CancelledError:
            return

    def close(self) -> None:
        if self._closed:
            return
        for stream_id, stream in list(self._streams.items()):
            self._send_stream_cancel(stream_id)
            stream._finish()
        self._streams.clear()
        for sub in list(self._subscriptions.values()):
            self._send_unsubscribe(sub)
            sub._finish(RpcSubscriptionState.CLOSED)
        self._subscriptions.clear()
        for sub in list(self._pending_subs):
            self._pending_subs.discard(sub)
            sub._finish(RpcSubscriptionState.CLOSED)
        for rpc_stream, _holder in list(self._pending_stream_calls.values()):
            rpc_stream.close()
        self._pending_stream_calls.clear()
        self._closed = True
        self._fail_in_flight()
        if self._handle is not None:
            self._handle.close()


__all__ = ["RpcSubscription", "RpcSubscriptionState", "RpcWsClient"]
