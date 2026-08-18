from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from webcompy.ajax._serde import from_json
from webcompy.hydration._transfer_meta import apply_transfer_meta, encode_with_meta
from webcompy.rpc._errors import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
)
from webcompy.rpc._registry import ProcedureRegistry

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


async def _process_entry(entry: Any, registry: ProcedureRegistry) -> dict[str, Any] | None:
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
            for response in [await _process_entry(entry, registry) for entry in payload]
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


def create_dispatcher_app(registry: ProcedureRegistry):
    """Return the JSON-RPC dispatcher as a bare ASGI application."""

    async def _app(scope: dict[str, Any], receive: Any, send: Any) -> None:
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
        status, response_body = await dispatch_body(body, registry)
        await _send_response(send, status, response_body, media_type="application/json")

    return _app


__all__ = ["create_dispatcher_app", "dispatch_body", "dispatch_payload"]
