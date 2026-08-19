from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any, Protocol

from webcompy.ajax._serde import from_json
from webcompy.ajax._sse import _format_sse_event
from webcompy.hydration._transfer_meta import apply_transfer_meta, encode_with_meta
from webcompy.rpc._errors import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
)
from webcompy.rpc._registry import ProcedureInfo, ProcedureRegistry

_logger = logging.getLogger(__name__)


class _DecodableProcedure(Protocol):
    @property
    def param_order(self) -> list[str]: ...

    @property
    def required(self) -> frozenset[str]: ...

    @property
    def param_schemas(self) -> dict[str, Any]: ...


class _ParamError(Exception):
    pass


def _error_body(req_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "error": error, "id": req_id}


def _valid_id(value: Any) -> bool:
    return value is None or (isinstance(value, (str, int, float)) and not isinstance(value, bool))


@dataclass(frozen=True)
class _StreamCall:
    """A validated single flagged streaming request handed to a transport."""

    info: ProcedureInfo
    kwargs: dict[str, Any]
    req_id: Any


def _classify_stream_call(
    payload: Any,
    registry: ProcedureRegistry,
) -> _StreamCall | dict[str, Any] | None:
    """Classify a single entry as a streaming call for a transport.

    Returns a ``_StreamCall`` for a valid single request with ``"stream": true``
    targeting a streaming procedure, a JSON-RPC error body when the request is a
    streaming call whose parameters are invalid, and ``None`` for everything else
    (batch arrays, notifications, mismatch cases, and ordinary requests), which
    the ordinary dispatch path handles.
    """
    if not isinstance(payload, dict) or payload.get("stream") is not True:
        return None
    if payload.get("jsonrpc") != "2.0" or not isinstance(payload.get("method"), str):
        return None
    req_id = payload.get("id")
    if "id" not in payload or not _valid_id(req_id):
        return None
    info = registry.get(payload["method"])
    if info is None or not info.is_streaming:
        return None
    params = payload.get("params")
    if params is not None and not isinstance(params, (list, dict)):
        return _error_body(req_id, INVALID_PARAMS, "Invalid params")
    meta = payload.get("meta")
    if meta is not None and not isinstance(meta, dict):
        return _error_body(req_id, INVALID_PARAMS, "Invalid params")
    try:
        kwargs = _decode_params(info, params, meta, registry)
    except _ParamError as err:
        return _error_body(req_id, INVALID_PARAMS, "Invalid params", str(err))
    return _StreamCall(info=info, kwargs=kwargs, req_id=req_id)


def _ensure_async_iter(generator: Any) -> AsyncGenerator[Any, None]:
    """Return an async generator over a streaming procedure's generator.

    Async generators are returned as-is; sync generators are wrapped so
    cancellation lands as ``GeneratorExit`` at their next yield.
    """
    if hasattr(generator, "__aiter__"):
        return generator

    async def _wrap() -> AsyncGenerator[Any, None]:
        try:
            for item in generator:
                yield item
                await asyncio.sleep(0)
        finally:
            generator.close()

    return _wrap()


def _decode_params(
    info: _DecodableProcedure,
    params: Any,
    meta: Any,
    registry: ProcedureRegistry,
) -> dict[str, Any]:
    if meta is not None:
        for tag in meta.values():
            if not isinstance(tag, str) or not registry.is_known_meta_tag(tag):
                raise _ParamError(f"unknown type tag {tag!r}")
        try:
            params = apply_transfer_meta(params, meta, strict=True, decoders=registry.meta_decoders)
        except ValueError as err:
            raise _ParamError(str(err)) from err
    if params is None:
        raw_kwargs: dict[str, Any] = {}
    elif isinstance(params, list):
        if len(params) > len(info.param_order):
            raise _ParamError("too many positional arguments")
        raw_kwargs = dict(zip(info.param_order, params, strict=False))
    elif isinstance(params, dict):
        raw_kwargs = dict(params)
    else:
        raise _ParamError("params must be an array or an object")
    missing = info.required - frozenset(raw_kwargs.keys())
    if missing:
        raise _ParamError(f"missing required parameter(s): {', '.join(sorted(missing))}")
    decoded: dict[str, Any] = {}
    for name, value in raw_kwargs.items():
        if name not in info.param_schemas:
            raise _ParamError(f"unknown parameter {name!r}")
        try:
            decoded[name] = from_json(info.param_schemas[name], value, strict=True)
        except (TypeError, ValueError) as err:
            raise _ParamError(str(err)) from err
    return decoded


async def _process_entry(entry: Any, registry: ProcedureRegistry, *, in_batch: bool = False) -> dict[str, Any] | None:
    if not isinstance(entry, dict):
        return _error_body(None, INVALID_REQUEST, "Invalid Request")
    has_id = "id" in entry
    req_id = entry.get("id")
    if has_id and not _valid_id(req_id):
        return _error_body(None, INVALID_REQUEST, "Invalid Request")
    if entry.get("jsonrpc") != "2.0" or not isinstance(entry.get("method"), str):
        return None if not has_id else _error_body(req_id, INVALID_REQUEST, "Invalid Request")
    method = entry["method"]
    params = entry.get("params")
    if params is not None and not isinstance(params, (list, dict)):
        return None if not has_id else _error_body(req_id, INVALID_PARAMS, "Invalid params")
    meta = entry.get("meta")
    if meta is not None and not isinstance(meta, dict):
        return None if not has_id else _error_body(req_id, INVALID_PARAMS, "Invalid params")
    info = registry.get(method)
    if info is None:
        if not has_id:
            return None
        return _error_body(req_id, METHOD_NOT_FOUND, "Method not found")
    if info.is_streaming:
        if not has_id:
            return None
        if in_batch:
            return _error_body(
                req_id,
                INVALID_REQUEST,
                f"RPC method {method!r} is a streaming procedure; streaming is not supported in batch requests",
            )
        if entry.get("stream") is not True:
            return _error_body(
                req_id,
                INVALID_REQUEST,
                f'RPC method {method!r} is a streaming procedure; send the request with "stream": true',
            )
        return _error_body(
            req_id,
            INVALID_REQUEST,
            f"RPC method {method!r} is a streaming procedure; the transport did not handle the stream",
        )
    if entry.get("stream") is True and has_id:
        return _error_body(req_id, INVALID_REQUEST, f"RPC method {method!r} is not a streaming procedure")
    try:
        kwargs = _decode_params(info, params, meta, registry)
    except _ParamError as err:
        if not has_id:
            return None
        return _error_body(req_id, INVALID_PARAMS, "Invalid params", str(err))
    try:
        result = info.func(**kwargs)
        if info.is_async:
            result = await result
        json_result, result_meta = encode_with_meta(result, type_handlers=registry.meta_encoders)
    except Exception:
        _logger.exception("RPC procedure %r failed", method)
        if not has_id:
            return None
        return _error_body(req_id, INTERNAL_ERROR, "Internal error")
    if not has_id:
        return None
    body: dict[str, Any] = {"jsonrpc": "2.0", "result": json_result, "id": req_id}
    if result_meta:
        body["meta"] = result_meta
    return body


def _json_response_body(data: Any) -> tuple[int, bytes]:
    return (200, json.dumps(data).encode("utf-8"))


async def dispatch_payload(
    payload: Any,
    registry: ProcedureRegistry,
) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Dispatch a parsed JSON-RPC payload (transport-neutral).

    ``payload`` is either a single request object or a batch array. Returns
    the response object(s) as plain JSON-serializable dictionaries, or ``None``
    when there is nothing to respond (e.g. notifications only). HTTP and
    WebSocket transports serialize the result to their own wire format.
    """
    if isinstance(payload, list):
        if not payload:
            return _error_body(None, INVALID_REQUEST, "Invalid Request")
        responses = [
            response
            for response in [await _process_entry(entry, registry, in_batch=True) for entry in payload]
            if response is not None
        ]
        return responses or None
    return await _process_entry(payload, registry)


async def dispatch_body(body: bytes, registry: ProcedureRegistry) -> tuple[int, bytes]:
    """Dispatch a raw JSON-RPC request body and return ``(status, response_body)``."""
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return _json_response_body(_error_body(None, PARSE_ERROR, "Parse error"))
    response = await dispatch_payload(payload, registry)
    if response is None:
        return (204, b"")
    return _json_response_body(response)


async def _read_body(receive: Any) -> bytes:
    chunks: list[bytes] = []
    more_body = True
    while more_body:
        message = await receive()
        if message["type"] != "http.request":
            break
        chunks.append(message.get("body", b""))
        more_body = message.get("more_body", False)
    return b"".join(chunks)


async def _send_response(
    send: Any,
    status: int,
    body: bytes,
    *,
    media_type: str,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
) -> None:
    headers: list[tuple[bytes, bytes]] = [
        (b"content-type", media_type.encode("latin-1")),
        (b"content-length", str(len(body)).encode("latin-1")),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


async def _run_sse_stream(
    call: _StreamCall,
    registry: ProcedureRegistry,
    receive: Any,
    send: Any,
) -> None:
    """Stream a streaming procedure call as Server-Sent Events."""
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"text/event-stream"),
                (b"cache-control", b"no-store"),
            ],
        }
    )
    agen = _ensure_async_iter(call.info.func(**call.kwargs))

    async def _pump() -> None:
        try:
            async for item in agen:
                json_data, meta = encode_with_meta(item, type_handlers=registry.meta_encoders)
                frame = _format_sse_event("item", json.dumps({"data": json_data, "meta": meta or None}))
                await send({"type": "http.response.body", "body": frame.encode("utf-8"), "more_body": True})
        except asyncio.CancelledError:
            raise
        except Exception:
            _logger.exception("RPC streaming procedure %r failed", call.info.name)
            try:
                frame = _format_sse_event(
                    "error",
                    json.dumps({"code": INTERNAL_ERROR, "message": "Internal error", "data": None}),
                )
                await send({"type": "http.response.body", "body": frame.encode("utf-8"), "more_body": True})
            except Exception:
                _logger.exception("RPC streaming procedure %r: failed to send error event", call.info.name)
        else:
            try:
                frame = _format_sse_event("done", "null")
                await send({"type": "http.response.body", "body": frame.encode("utf-8"), "more_body": True})
            except Exception:
                _logger.exception("RPC streaming procedure %r: failed to send done event", call.info.name)

    async def _watch_disconnect() -> None:
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return

    pump_task = asyncio.create_task(_pump())
    watch_task = asyncio.create_task(_watch_disconnect())
    try:
        await asyncio.wait({pump_task, watch_task}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        pump_task.cancel()
        watch_task.cancel()
        await asyncio.gather(pump_task, watch_task, return_exceptions=True)
        await agen.aclose()
    with contextlib.suppress(Exception):
        await send({"type": "http.response.body", "body": b"", "more_body": False})


class _DispatcherASGIApp:
    def __init__(self, registry: ProcedureRegistry) -> None:
        self._registry = registry

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await _send_response(send, 404, b"", media_type="text/plain")
            return
        if scope["method"] != "POST":
            await _send_response(
                send,
                405,
                b"",
                media_type="text/plain",
                extra_headers=[(b"allow", b"POST")],
            )
            return
        body = await _read_body(receive)
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            await _send_response(
                send,
                200,
                _json_response_body(_error_body(None, PARSE_ERROR, "Parse error"))[1],
                media_type="application/json",
            )
            return
        classified = _classify_stream_call(payload, self._registry)
        if isinstance(classified, dict):
            await _send_response(send, 200, json.dumps(classified).encode("utf-8"), media_type="application/json")
            return
        if classified is not None:
            await _run_sse_stream(classified, self._registry, receive, send)
            return
        response = await dispatch_payload(payload, self._registry)
        if response is None:
            await _send_response(send, 204, b"", media_type="application/json")
            return
        await _send_response(send, 200, json.dumps(response).encode("utf-8"), media_type="application/json")


def create_dispatcher_app(registry: ProcedureRegistry):
    """Return the JSON-RPC dispatcher as a class-based ASGI application.

    The returned app is usable directly as an ASGI application or as the
    endpoint of a Starlette ``Route`` (which dispatches to class-based ASGI
    apps verbatim). It serves ordinary JSON-RPC responses as ``application/json``
    and single ``"stream": true`` calls to streaming procedures as
    ``text/event-stream``.
    """
    return _DispatcherASGIApp(registry)


__all__ = ["create_dispatcher_app", "dispatch_body", "dispatch_payload"]
