from __future__ import annotations

import asyncio
import itertools
import logging
from collections.abc import AsyncGenerator
from typing import Any

from webcompy.hydration._transfer_meta import encode_with_meta
from webcompy.rpc._errors import INTERNAL_ERROR, RpcError
from webcompy.rpc._registry import ProcedureRegistry
from webcompy.rpc._stream import STREAM_CANCEL_METHOD, STREAM_DONE_METHOD, STREAM_ERROR_METHOD
from webcompy_server.rpc._dispatcher import _ensure_async_iter, _StreamCall
from webcompy_server.rpc._subscriptions import EVENT_METHOD, _Connection

_logger = logging.getLogger(__name__)


def _stream_event_frame(stream_id: str, data: Any, meta: dict[str, str] | None) -> dict[str, Any]:
    params: dict[str, Any] = {"stream_id": stream_id, "data": data}
    if meta:
        params["meta"] = meta
    return {"jsonrpc": "2.0", "method": EVENT_METHOD, "params": params}


class StreamCallHub:
    """Run per-call streaming procedures over a shared WebSocket connection.

    Each flagged call spawns its own generator task on the caller's
    ``_Connection``. Streams are never shared, replayed, or given an idle
    grace period; cancellation (via ``_webcompy.stream_cancel`` or socket
    close) stops the generator immediately.
    """

    def __init__(self, registry: ProcedureRegistry) -> None:
        self.registry = registry
        self._stream_counter = itertools.count(1)

    def start_call(self, conn: _Connection, call: _StreamCall) -> None:
        stream_id = f"st{next(self._stream_counter)}"
        conn.send({"jsonrpc": "2.0", "result": {"stream_id": stream_id}, "id": call.req_id})
        task = asyncio.create_task(self._run(conn, stream_id, call))
        conn.stream_tasks[stream_id] = task
        task.add_done_callback(lambda _t, c=conn, sid=stream_id: c.stream_tasks.pop(sid, None))

    def handle_cancel(self, conn: _Connection, payload: dict[str, Any]) -> None:
        params = payload.get("params")
        if not isinstance(params, dict):
            return
        stream_id = params.get("stream_id")
        if not isinstance(stream_id, str):
            return
        task = conn.stream_tasks.pop(stream_id, None)
        if task is not None:
            task.cancel()

    async def _run(self, conn: _Connection, stream_id: str, call: _StreamCall) -> None:
        agen: AsyncGenerator[Any, None] | None = None
        try:
            agen = _ensure_async_iter(call.info.func(**call.kwargs))
            async for item in agen:
                json_data, meta = encode_with_meta(item, type_handlers=self.registry.meta_encoders)
                conn.send(_stream_event_frame(stream_id, json_data, meta or None))
            conn.send({"jsonrpc": "2.0", "method": STREAM_DONE_METHOD, "params": {"stream_id": stream_id}})
        except asyncio.CancelledError:
            raise
        except RpcError as err:
            _logger.warning("RPC streaming procedure %r failed", call.info.name, exc_info=err)
            conn.send(
                {
                    "jsonrpc": "2.0",
                    "method": STREAM_ERROR_METHOD,
                    "params": {
                        "stream_id": stream_id,
                        "code": err.code,
                        "message": err.message,
                        "data": err.data,
                    },
                }
            )
        except Exception:
            _logger.exception("RPC streaming procedure %r failed", call.info.name)
            conn.send(
                {
                    "jsonrpc": "2.0",
                    "method": STREAM_ERROR_METHOD,
                    "params": {"stream_id": stream_id, "code": INTERNAL_ERROR, "message": "Internal error"},
                }
            )
        finally:
            if agen is not None:
                await agen.aclose()


__all__ = [
    "STREAM_CANCEL_METHOD",
    "STREAM_DONE_METHOD",
    "STREAM_ERROR_METHOD",
    "StreamCallHub",
]
