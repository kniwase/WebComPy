from __future__ import annotations

import asyncio
import warnings
from collections.abc import Mapping
from json import JSONDecodeError
from json import dumps as json_dumps
from json import loads as json_loads
from typing import Any, TypeVar, overload

from webcompy.aio._aio import _aio_run_task
from webcompy.ajax._serde import from_json
from webcompy.ajax._sse import _SSEParser
from webcompy.di import inject
from webcompy.di._keys import RPC_REGISTRY_KEY
from webcompy.hydration._transfer_meta import apply_transfer_meta, encode_with_meta
from webcompy.ports._fetch import FetchStream
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy.rpc._errors import INTERNAL_ERROR, SERVER_ERROR, RpcError
from webcompy.rpc._registry import ProcedureRegistry
from webcompy.rpc._stream import RpcStream, _decode_stream_item
from webcompy.utils._environment import ENVIRONMENT

T = TypeVar("T")


def _registry_or_error() -> ProcedureRegistry:
    registry = inject(RPC_REGISTRY_KEY, default=None)
    if not isinstance(registry, ProcedureRegistry):
        raise RpcError(SERVER_ERROR, "RPC registry is not available in the current DI scope")
    return registry


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


async def _post_envelope(registry: ProcedureRegistry, payload: Any) -> Any:
    fetch_port = inject(FETCH_PORT_KEY, default=None)
    if fetch_port is None:
        raise RpcError(SERVER_ERROR, "FetchPort is not available in the current DI scope")
    body = json_dumps(payload, ensure_ascii=True)
    response = await fetch_port.fetch(
        registry.endpoint_url,
        method="POST",
        headers={"Content-Type": "application/json"},
        body=body,
    )
    if response.status_code == 204 or not response.text:
        return None
    try:
        return json_loads(response.text)
    except JSONDecodeError as err:
        raise RpcError(SERVER_ERROR, f"Invalid JSON-RPC response (HTTP {response.status_code})") from err


@overload
async def _call_impl(
    method: str,
    params: Any | None = None,
    *,
    result_type: None = None,
) -> Any: ...


@overload
async def _call_impl(
    method: str,
    params: Any | None = None,
    *,
    result_type: type[T],
) -> T: ...


async def _call_impl(
    method: str,
    params: Any | None = None,
    *,
    result_type: type[T] | None = None,
) -> Any:
    registry = _registry_or_error()
    envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "id": registry.next_id()}
    if params is not None:
        _encode_params(registry, envelope, params)
    data = await _post_envelope(registry, envelope)
    if data is None:
        raise RpcError(SERVER_ERROR, "Empty response for RPC call")
    return _resolve_single(data, result_type, registry)


async def _notify_impl(
    method: str,
    params: Any | None = None,
) -> None:
    registry = _registry_or_error()
    envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        _encode_params(registry, envelope, params)
    await _post_envelope(registry, envelope)


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


@overload
async def _stream_impl(
    method: str,
    params: Any | None = None,
    *,
    result_type: None = None,
) -> RpcStream[Any]: ...


@overload
async def _stream_impl(
    method: str,
    params: Any | None = None,
    *,
    result_type: type[T],
) -> RpcStream[T]: ...


async def _stream_impl(
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
    envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "id": registry.next_id(), "stream": True}
    if params is not None:
        _encode_params(registry, envelope, params)
    fetch_stream = await fetch_port.stream(
        registry.endpoint_url,
        method="POST",
        headers={"Content-Type": "application/json"},
        body=json_dumps(envelope, ensure_ascii=True),
    )
    if not fetch_stream.ok:
        fetch_stream.close()
        raise RpcError(SERVER_ERROR, f"RPC stream request failed (HTTP {fetch_stream.status_code})")
    if _is_event_stream(fetch_stream.headers):
        holder: dict[str, Any] = {}

        def _cancel() -> None:
            task = holder.get("task")
            if task is not None:
                task.cancel()
            fetch_stream.close()

        rpc_stream: RpcStream[Any] = RpcStream(
            cancel=_cancel,
            decode=lambda data, meta: _decode_stream_item(data, meta, result_type, registry),
        )
        task = _aio_run_task(_pump_sse(fetch_stream, rpc_stream))
        if task is None:
            fetch_stream.close()
            raise RuntimeError("webcompy rpc: cannot schedule the stream pump without a running event loop")
        holder["task"] = task
        return rpc_stream
    chunks = [chunk async for chunk in fetch_stream]
    fetch_stream.close()
    try:
        data = json_loads("".join(chunks))
    except JSONDecodeError as err:
        raise RpcError(SERVER_ERROR, "Invalid JSON-RPC response for stream request") from err
    _resolve_single(data, result_type, registry)
    raise RpcError(SERVER_ERROR, "RPC server did not accept the stream request")


__all__ = ["_call_impl", "_notify_impl", "_post_envelope", "_registry_or_error", "_resolve_single", "_stream_impl"]
