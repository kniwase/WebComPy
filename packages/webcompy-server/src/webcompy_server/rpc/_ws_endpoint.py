from __future__ import annotations

import json

from webcompy.rpc._errors import PARSE_ERROR
from webcompy.rpc._registry import ProcedureRegistry
from webcompy.rpc._stream import STREAM_CANCEL_METHOD
from webcompy_server.rpc._dispatcher import _classify_stream_call, _error_body, dispatch_payload
from webcompy_server.rpc._streams import StreamCallHub
from webcompy_server.rpc._subscriptions import SubscriptionHub

CLOSE_METHOD = "_webcompy.close"
SUBSCRIBE_METHOD = "_webcompy.subscribe"
UNSUBSCRIBE_METHOD = "_webcompy.unsubscribe"
PING_METHOD = "_webcompy.ping"
PONG_METHOD = "_webcompy.pong"


def create_rpc_ws_endpoint(registry: ProcedureRegistry):
    """Return the JSON-RPC WebSocket endpoint handler for ``registry``.

    The endpoint accepts a WebSocket, feeds each incoming text frame through
    the shared transport-neutral dispatch core (``dispatch_payload``) and
    writes each response back as a text frame via a per-connection send queue
    (single FIFO path guarantees response → replay → live ordering for
    subscriptions). Reserved ``_webcompy.*`` methods are handled here: ping is
    answered with pong, close closes the socket with code 1011 so the client
    reconnect loop engages, subscribe/unsubscribe drive the subscription
    hub, and stream-cancel stops a per-call stream. Single ``"stream": true``
    calls to streaming procedures are answered with a ``stream_id`` and
    streamed by the ``StreamCallHub``. Starlette is imported lazily so this
    module stays importable outside a Starlette context.
    """
    from starlette.websockets import WebSocket, WebSocketDisconnect

    hub = SubscriptionHub(registry)
    stream_hub = StreamCallHub(registry)

    async def endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        conn = hub.attach(websocket)
        try:
            while True:
                message = await websocket.receive()
                if message["type"] != "websocket.receive":
                    break
                text = message.get("text")
                if text is None:
                    continue
                try:
                    payload = json.loads(text)
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                    conn.send(_error_body(None, PARSE_ERROR, "Parse error"))
                    continue
                if isinstance(payload, dict):
                    method = payload.get("method")
                    if method == CLOSE_METHOD:
                        await websocket.close(code=1011)
                        return
                    if method == PING_METHOD:
                        conn.send({"jsonrpc": "2.0", "method": PONG_METHOD, "params": {}})
                        continue
                    if method == PONG_METHOD:
                        continue
                    if method == SUBSCRIBE_METHOD:
                        hub.handle_subscribe(conn, payload)
                        continue
                    if method == UNSUBSCRIBE_METHOD:
                        hub.handle_unsubscribe(conn, payload)
                        continue
                    if method == STREAM_CANCEL_METHOD:
                        stream_hub.handle_cancel(conn, payload)
                        continue
                    classified = _classify_stream_call(payload, registry)
                    if isinstance(classified, dict):
                        conn.send(classified)
                        continue
                    if classified is not None:
                        stream_hub.start_call(conn, classified)
                        continue
                response = await dispatch_payload(payload, registry)
                if response is not None:
                    conn.send(response)
        except WebSocketDisconnect:
            pass
        finally:
            await conn.close()

    return endpoint


__all__ = ["create_rpc_ws_endpoint"]
