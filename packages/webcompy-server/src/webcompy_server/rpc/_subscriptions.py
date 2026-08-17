from __future__ import annotations

import asyncio
import itertools
import json
import logging
from collections import deque
from typing import Any

from webcompy.hydration._transfer_meta import encode_with_meta
from webcompy.rpc._errors import INVALID_PARAMS, INVALID_REQUEST, METHOD_NOT_FOUND
from webcompy.rpc._registry import ProcedureRegistry, SubscriptionInfo
from webcompy_server.rpc._dispatcher import _decode_params, _error_body, _ParamError

_logger = logging.getLogger(__name__)

EVENT_METHOD = "_webcompy.event"

_STREAM_IDLE_TIMEOUT = 60.0

_sub_counter = itertools.count(1)


def _event_frame(sub_id: str, cursor: int, data: Any, meta: dict[str, str] | None) -> dict[str, Any]:
    params: dict[str, Any] = {"subscription_id": sub_id, "cursor": cursor, "data": data}
    if meta:
        params["meta"] = meta
    return {"jsonrpc": "2.0", "method": EVENT_METHOD, "params": params}


class _Stream:
    def __init__(self, hub: SubscriptionHub, info: SubscriptionInfo, params_key: str, kwargs: dict[str, Any]) -> None:
        self.hub = hub
        self.info = info
        self.params_key = params_key
        self.kwargs = kwargs
        self.cursor = 0
        self.buffer: deque[tuple[int, Any, dict[str, str] | None]] = deque(maxlen=info.replay_size)
        self.subscribers: dict[str, asyncio.Queue] = {}
        self.source_task: asyncio.Task | None = None
        self.idle_task: asyncio.Task | None = None

    def start_source(self) -> None:
        encoders = self.hub.registry.meta_encoders

        async def _run() -> None:
            try:
                async for event in self.info.func(**self.kwargs):
                    json_data, meta = encode_with_meta(event, type_handlers=encoders)
                    self.cursor += 1
                    self.buffer.append((self.cursor, json_data, meta or None))
                    for sub_id, queue in list(self.subscribers.items()):
                        queue.put_nowait(_event_frame(sub_id, self.cursor, json_data, meta or None))
            except asyncio.CancelledError:
                raise
            except Exception:
                _logger.exception("RPC subscription %r failed", self.info.name)

        self.source_task = asyncio.create_task(_run())

    def check_rejoin(self, last_cursor: int) -> tuple[list[tuple[int, Any, dict[str, str] | None]], bool]:
        if last_cursor == self.cursor:
            return [], False
        if last_cursor > self.cursor or not self.buffer:
            return [], True
        oldest = self.buffer[0][0]
        if last_cursor < oldest:
            return [], True
        return [(c, d, m) for c, d, m in self.buffer if c > last_cursor], False

    def attach(self, sub_id: str, queue: asyncio.Queue) -> None:
        if self.idle_task is not None:
            self.idle_task.cancel()
            self.idle_task = None
        self.subscribers[sub_id] = queue

    def detach(self, sub_id: str) -> None:
        self.subscribers.pop(sub_id, None)
        if not self.subscribers and self.source_task is not None and not self.source_task.done():
            self.schedule_idle()

    def schedule_idle(self) -> None:
        if self.idle_task is not None:
            return

        async def _idle() -> None:
            await asyncio.sleep(_STREAM_IDLE_TIMEOUT)
            if not self.subscribers:
                self.hub.reap(self)

        self.idle_task = asyncio.create_task(_idle())


class SubscriptionHub:
    def __init__(self, registry: ProcedureRegistry) -> None:
        self.registry = registry
        self._streams: dict[tuple[str, str], _Stream] = {}

    def attach(self, websocket: Any) -> _Connection:
        conn = _Connection(self, websocket)
        conn.start_sender()
        return conn

    def handle_subscribe(self, conn: _Connection, payload: dict[str, Any]) -> None:
        req_id = payload.get("id")
        params = payload.get("params")
        if not isinstance(params, dict):
            conn.send(_error_body(req_id, INVALID_REQUEST, "Invalid params"))
            return
        method = params.get("method")
        if not isinstance(method, str):
            conn.send(_error_body(req_id, INVALID_REQUEST, "Invalid params"))
            return
        info = self.registry.get_subscription(method)
        if info is None:
            conn.send(_error_body(req_id, METHOD_NOT_FOUND, "Method not found"))
            return
        raw_params = params.get("params")
        meta = params.get("meta")
        if meta is not None and not isinstance(meta, dict):
            conn.send(_error_body(req_id, INVALID_PARAMS, "Invalid params"))
            return
        try:
            kwargs = _decode_params(info, raw_params, meta, self.registry)
        except _ParamError as err:
            conn.send(_error_body(req_id, INVALID_PARAMS, "Invalid params", str(err)))
            return
        last_cursor = params.get("last_cursor")
        if last_cursor is not None and (isinstance(last_cursor, bool) or not isinstance(last_cursor, int)):
            conn.send(_error_body(req_id, INVALID_PARAMS, "Invalid params"))
            return
        params_key = json.dumps(raw_params, sort_keys=True)
        stream = self._streams.get((method, params_key))
        if stream is None:
            stream = _Stream(self, info, params_key, kwargs)
            self._streams[(method, params_key)] = stream
            stream.start_source()
        if last_cursor is not None:
            replay, resync = stream.check_rejoin(last_cursor)
            if resync:
                conn.send(
                    {
                        "jsonrpc": "2.0",
                        "result": {"subscription_id": None, "resync_required": True},
                        "id": req_id,
                    }
                )
                return
        else:
            replay = []
        sub_id = f"s{next(_sub_counter)}"
        conn.send({"jsonrpc": "2.0", "result": {"subscription_id": sub_id, "resync_required": False}, "id": req_id})
        for cursor, data, event_meta in replay:
            conn.send(_event_frame(sub_id, cursor, data, event_meta))
        stream.attach(sub_id, conn.queue)
        conn.subscriptions[sub_id] = stream

    def handle_unsubscribe(self, conn: _Connection, payload: dict[str, Any]) -> None:
        params = payload.get("params")
        if not isinstance(params, dict):
            return
        sub_id = params.get("subscription_id")
        if not isinstance(sub_id, str):
            return
        stream = conn.subscriptions.pop(sub_id, None)
        if stream is not None:
            stream.detach(sub_id)

    def reap(self, stream: _Stream) -> None:
        if stream.subscribers:
            return
        self._streams.pop((stream.info.name, stream.params_key), None)
        if stream.source_task is not None:
            stream.source_task.cancel()
        if stream.idle_task is not None:
            stream.idle_task.cancel()


class _Connection:
    def __init__(self, hub: SubscriptionHub, websocket: Any) -> None:
        self.hub = hub
        self.websocket = websocket
        self.queue: asyncio.Queue = asyncio.Queue()
        self.subscriptions: dict[str, _Stream] = {}
        self.sender_task: asyncio.Task | None = None

    def start_sender(self) -> None:
        websocket = self.websocket

        async def _drain() -> None:
            try:
                while True:
                    frame = await self.queue.get()
                    await websocket.send_text(json.dumps(frame))
            except asyncio.CancelledError:
                raise
            except Exception:
                _logger.exception("RPC WebSocket sender failed")

        self.sender_task = asyncio.create_task(_drain())

    def send(self, frame: Any) -> None:
        self.queue.put_nowait(frame)

    async def close(self) -> None:
        for sub_id in list(self.subscriptions):
            stream = self.subscriptions.pop(sub_id, None)
            if stream is not None:
                stream.detach(sub_id)
        if self.sender_task is not None:
            self.sender_task.cancel()


__all__ = ["SubscriptionHub"]
