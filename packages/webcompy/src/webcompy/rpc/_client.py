"""Browser-side JSON-RPC 2.0 messaging over HTTP fetch and SSE."""

from __future__ import annotations

import asyncio
import warnings
from collections.abc import Mapping
from json import JSONDecodeError
from json import dumps as json_dumps
from json import loads as json_loads
from typing import Any, TypeVar, cast

from webcompy.aio._aio import _aio_run_task
from webcompy.ajax._serde import from_json
from webcompy.ajax._sse import _SSEParser
from webcompy.di import inject
from webcompy.di._keys import RPC_MIDDLEWARE_KEY, RPC_REGISTRY_KEY
from webcompy.hydration._transfer_meta import apply_transfer_meta, encode_with_meta
from webcompy.ports._fetch import FetchStream
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy.rpc._errors import INTERNAL_ERROR, SERVER_ERROR, RpcError
from webcompy.rpc._middleware import (
    RpcContext,
    merge_extra_headers,
    run_rpc_middlewares,
)
from webcompy.rpc._registry import ProcedureRegistry
from webcompy.rpc._stream import RpcStream, _decode_stream_item
from webcompy.utils._environment import ENVIRONMENT

T = TypeVar("T")


def _registry_or_error() -> ProcedureRegistry:
    registry = inject(RPC_REGISTRY_KEY, default=None)
    if not isinstance(registry, ProcedureRegistry):
        raise RpcError(SERVER_ERROR, "RPC registry is not available in the current DI scope")
    return registry


def _rpc_middlewares() -> tuple[Any, ...]:
    registry = inject(RPC_MIDDLEWARE_KEY, default=None)
    if registry is None:
        return ()
    return tuple(getattr(registry, "middlewares", ()))


def _encode_params(registry: ProcedureRegistry, envelope: dict[str, Any], params: Any) -> None:
    json_params, meta = encode_with_meta(params, type_handlers=registry.meta_encoders)
    envelope["params"] = json_params
    if meta:
        envelope["meta"] = meta


def _resolve_single(data: Any, result_type: type[T] | None, registry: ProcedureRegistry) -> Any:
    if not isinstance(data, dict) or data.get("jsonrpc") != "2.0":
        raise RpcError(SERVER_ERROR, "Malformed JSON-RPC response")
    if "error" in data:
        error = data["error"]
        if not isinstance(error, dict):
            raise RpcError(SERVER_ERROR, "Malformed JSON-RPC error response")
        code = error.get("code", INTERNAL_ERROR)
        message = error.get("message", "Unknown error")
        if not isinstance(code, int) or not isinstance(message, str):
            raise RpcError(SERVER_ERROR, "Malformed JSON-RPC error response")
        raise RpcError(code, message, error.get("data"))
    result = data.get("result")
    meta = data.get("meta")
    if meta is not None:
        if not isinstance(meta, Mapping):
            raise RpcError(SERVER_ERROR, "Malformed meta in RPC response")
        try:
            result = apply_transfer_meta(result, meta, strict=False, decoders=registry.meta_decoders)
        except ValueError as err:
            raise RpcError(INTERNAL_ERROR, f"Failed to apply response meta: {err}") from err
    if result_type is None:
        return result
    try:
        return from_json(result_type, result)
    except (TypeError, ValueError) as err:
        raise RpcError(INTERNAL_ERROR, f"RPC result does not match schema: {err}") from err


async def _post_envelope(registry: ProcedureRegistry, payload: Any, extra_headers: dict[str, str] | None = None) -> Any:
    fetch_port = inject(FETCH_PORT_KEY, default=None)
    if fetch_port is None:
        raise RpcError(SERVER_ERROR, "FetchPort is not available in the current DI scope")
    body = json_dumps(payload, ensure_ascii=True)
    response = await fetch_port.fetch(
        registry.endpoint_url,
        method="POST",
        headers=merge_extra_headers(extra_headers),
        body=body,
    )
    if response.status_code == 204 or not response.text:
        return None
    try:
        return json_loads(response.text)
    except JSONDecodeError as err:
        raise RpcError(SERVER_ERROR, f"Invalid JSON-RPC response (HTTP {response.status_code})") from err


async def _call_impl(
    method: str,
    params: Any | None = None,
    *,
    result_type: type[T] | None = None,
) -> Any:
    registry = _registry_or_error()
    ctx = RpcContext(method=method, params=params, result_type=result_type)

    async def terminal(context: RpcContext) -> Any:
        envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": context.method, "id": registry.next_id()}
        if context.params is not None:
            _encode_params(registry, envelope, context.params)
        data = await _post_envelope(registry, envelope, extra_headers=context.headers)
        if data is None:
            raise RpcError(SERVER_ERROR, "Empty response for RPC call")
        return _resolve_single(data, context.result_type, registry)

    async def synthesize(fragment: Any, context: RpcContext) -> Any:
        normalized = {"jsonrpc": "2.0", **fragment} if isinstance(fragment, Mapping) else fragment
        return _resolve_single(normalized, context.result_type, registry)

    return await run_rpc_middlewares(_rpc_middlewares(), ctx, terminal, synthesize)


async def _notify_impl(
    method: str,
    params: Any | None = None,
) -> None:
    registry = _registry_or_error()
    ctx = RpcContext(method=method, params=params)

    async def terminal(context: RpcContext) -> None:
        envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": context.method}
        if context.params is not None:
            _encode_params(registry, envelope, context.params)
        await _post_envelope(registry, envelope, extra_headers=context.headers)

    async def synthesize(_fragment: Any, _context: RpcContext) -> None:
        return None

    await run_rpc_middlewares(_rpc_middlewares(), ctx, terminal, synthesize)


_SSR_STREAM_MSG = "webcompy rpc: rpc.stream called outside the browser; returning an empty closed stream"


def _is_event_stream(headers: Mapping[str, str]) -> bool:
    content_type = next((value for key, value in headers.items() if key.lower() == "content-type"), "")
    return content_type.split(";")[0].strip().lower() == "text/event-stream"


async def _pump_sse(fetch_stream: FetchStream, rpc_stream: RpcStream[Any]) -> None:
    parser = _SSEParser()
    try:
        async for chunk in fetch_stream:
            for event in parser.feed(chunk):
                if event.event_type == "item":
                    try:
                        payload = json_loads(event.data)
                    except ValueError:
                        rpc_stream._fail(RpcError(SERVER_ERROR, "Malformed RPC stream item frame"))
                        return
                    if not isinstance(payload, dict) or "data" not in payload:
                        rpc_stream._fail(RpcError(SERVER_ERROR, "Malformed RPC stream item frame"))
                        return
                    rpc_stream._deliver_raw(payload.get("data"), payload.get("meta"))
                elif event.event_type == "done":
                    rpc_stream._finish()
                    return
                elif event.event_type == "error":
                    try:
                        payload = json_loads(event.data)
                    except ValueError:
                        rpc_stream._fail(RpcError(SERVER_ERROR, "Malformed RPC stream error frame"))
                        return
                    if not isinstance(payload, dict):
                        rpc_stream._fail(RpcError(SERVER_ERROR, "Malformed RPC stream error frame"))
                        return
                    code = payload.get("code")
                    message = payload.get("message")
                    if not isinstance(code, int) or not isinstance(message, str):
                        rpc_stream._fail(RpcError(SERVER_ERROR, "Malformed RPC stream error frame"))
                        return
                    rpc_stream._fail(RpcError(code, message, payload.get("data")))
                    return
        rpc_stream._fail(RpcError(SERVER_ERROR, "RPC stream ended unexpectedly"))
    except asyncio.CancelledError:
        raise
    except Exception as err:
        rpc_stream._fail(RpcError(SERVER_ERROR, f"RPC stream failed: {err}"))
    finally:
        fetch_stream.close()


def _stream_impl(
    method: str,
    params: Any | None = None,
    *,
    result_type: type[T] | None = None,
) -> RpcStream[Any]:
    registry = _registry_or_error()
    fetch_port = inject(FETCH_PORT_KEY, default=None)
    if fetch_port is None or (ENVIRONMENT != "pyscript" and getattr(fetch_port, "noop", False)):
        warnings.warn(_SSR_STREAM_MSG, UserWarning, stacklevel=2)
        return RpcStream(closed=True)
    holder: dict[str, Any] = {}

    def _cancel() -> None:
        holder["cancelled"] = True
        task = holder.get("task")
        if task is not None:
            task.cancel()
        fetch_stream = holder.get("fetch_stream")
        if fetch_stream is not None:
            fetch_stream.close()

    rpc_stream: RpcStream[Any] = RpcStream(
        cancel=_cancel,
        decode=lambda data, meta: _decode_stream_item(data, meta, result_type, registry),
    )

    async def _setup_and_pump() -> None:
        try:
            ctx = RpcContext(method=method, params=params, result_type=result_type)

            async def terminal(context: RpcContext) -> FetchStream:
                envelope: dict[str, Any] = {
                    "jsonrpc": "2.0",
                    "method": context.method,
                    "id": registry.next_id(),
                    "stream": True,
                }
                if context.params is not None:
                    _encode_params(registry, envelope, context.params)
                return await fetch_port.stream(  # type: ignore[union-attr]
                    registry.endpoint_url,
                    method="POST",
                    headers=merge_extra_headers(context.headers),
                    body=json_dumps(envelope, ensure_ascii=True),
                )

            async def synthesize(stream_obj: Any, _context: RpcContext) -> FetchStream:
                return cast("FetchStream", stream_obj)

            fetch_stream = await run_rpc_middlewares(_rpc_middlewares(), ctx, terminal, synthesize)
            holder["fetch_stream"] = fetch_stream
            if holder.get("cancelled") or rpc_stream._finished:
                fetch_stream.close()
                return
            if not fetch_stream.ok:
                fetch_stream.close()
                rpc_stream._fail(RpcError(SERVER_ERROR, f"RPC stream request failed (HTTP {fetch_stream.status_code})"))
                return
            if _is_event_stream(fetch_stream.headers):
                await _pump_sse(fetch_stream, rpc_stream)
                return
            chunks = [chunk async for chunk in fetch_stream]
            fetch_stream.close()
            try:
                data = json_loads("".join(chunks))
            except JSONDecodeError:
                rpc_stream._fail(RpcError(SERVER_ERROR, "Invalid JSON-RPC response for stream request"))
                return
            try:
                _resolve_single(data, result_type, registry)
            except RpcError as err:
                rpc_stream._fail(err)
                return
            rpc_stream._fail(RpcError(SERVER_ERROR, "RPC server did not accept the stream request"))
        except asyncio.CancelledError:
            raise
        except Exception as err:
            rpc_stream._fail(RpcError(SERVER_ERROR, f"RPC stream failed: {err}"))

    task = _aio_run_task(_setup_and_pump())
    if task is None:
        raise RuntimeError("webcompy rpc: cannot schedule the stream pump without a running event loop")
    holder["task"] = task
    return rpc_stream


__all__ = ["_call_impl", "_notify_impl", "_post_envelope", "_registry_or_error", "_resolve_single", "_stream_impl"]
