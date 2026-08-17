from __future__ import annotations

import json
import logging
from typing import Any

from webcompy.rpc._errors import PARSE_ERROR
from webcompy.rpc._registry import ProcedureRegistry
from webcompy_server.rpc._dispatcher import _error_body, dispatch_payload

_logger = logging.getLogger(__name__)

PING_METHOD = "_webcompy.ping"
PONG_METHOD = "_webcompy.pong"
CLOSE_METHOD = "_webcompy.close"
SUBSCRIBE_METHOD = "_webcompy.subscribe"
UNSUBSCRIBE_METHOD = "_webcompy.unsubscribe"
EVENT_METHOD = "_webcompy.event"


def create_rpc_ws_endpoint(registry: ProcedureRegistry, *, subscriptions: Any = None):
    """Return the JSON-RPC WebSocket endpoint handler for ``registry``.

    The endpoint accepts a WebSocket, feeds each incoming text frame through
    the shared transport-neutral dispatch core (``dispatch_payload``) and
    writes each response back as a text frame. Reserved ``_webcompy.*``
    methods are handled by the endpoint itself; ``subscriptions`` (a
    ``SubscriptionHub``) additionally handles subscribe/unsubscribe when
    provided. Starlette is imported lazily so this module stays importable
    outside a Starlette context.
    """
    from starlette.websockets import WebSocket, WebSocketDisconnect

    async def _pong_frame() -> str:
        return json.dumps({"jsonrpc": "2.0", "method": PONG_METHOD, "params": {}})

    async def endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        connection = subscriptions.attach(websocket) if subscriptions is not None else None
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
                    await websocket.send_text(json.dumps(_error_body(None, PARSE_ERROR, "Parse error")))
                    continue
                if isinstance(payload, dict):
                    method = payload.get("method")
                    if method == CLOSE_METHOD:
                        await websocket.close(code=1011)
                        return
                    if method == PING_METHOD:
                        await websocket.send_text(await _pong_frame())
                        continue
                    if method == PONG_METHOD:
                        continue
                    if method in (SUBSCRIBE_METHOD, UNSUBSCRIBE_METHOD) and subscriptions is not None:
                        await subscriptions.handle(connection, payload, websocket)
                        continue
                response = await dispatch_payload(payload, registry)
                if response is not None:
                    await websocket.send_text(json.dumps(response))
        except WebSocketDisconnect:
            pass
        finally:
            if connection is not None:
                await connection.close()

    return endpoint


__all__ = ["create_rpc_ws_endpoint"]
