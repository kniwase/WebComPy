from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence
from json import JSONDecodeError
from json import dumps as json_dumps
from json import loads as json_loads
from typing import Any, TypeVar, overload

from webcompy.ajax._serde import from_json
from webcompy.di import inject
from webcompy.di._keys import RPC_REGISTRY_KEY
from webcompy.hydration._transfer_meta import apply_transfer_meta, encode_with_meta
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy.rpc._errors import INTERNAL_ERROR, SERVER_ERROR, RpcError
from webcompy.rpc._registry import ProcedureRegistry

T = TypeVar("T")

_id_counter = itertools.count(1)


def _next_id() -> int:
    return next(_id_counter)


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
async def call(
    method: str,
    params: Mapping[str, Any] | Sequence[Any] | None = None,
    *,
    result_type: None = None,
) -> Any: ...


@overload
async def call(
    method: str,
    params: Mapping[str, Any] | Sequence[Any] | None = None,
    *,
    result_type: type[T],
) -> T: ...


async def call(
    method: str,
    params: Mapping[str, Any] | Sequence[Any] | None = None,
    *,
    result_type: type[T] | None = None,
) -> Any:
    registry = _registry_or_error()
    envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "id": _next_id()}
    if params is not None:
        _encode_params(registry, envelope, params)
    data = await _post_envelope(registry, envelope)
    if data is None:
        raise RpcError(SERVER_ERROR, "Empty response for RPC call")
    return _resolve_single(data, result_type, registry)


async def notify(
    method: str,
    params: Mapping[str, Any] | Sequence[Any] | None = None,
) -> None:
    registry = _registry_or_error()
    envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        _encode_params(registry, envelope, params)
    await _post_envelope(registry, envelope)


async def batch(calls: Sequence[tuple[str, Any] | tuple[str, Any, type[Any]]]) -> list[Any]:
    registry = _registry_or_error()
    envelopes: list[dict[str, Any]] = []
    entries: list[tuple[int, type[Any] | None]] = []
    for call_spec in calls:
        method = call_spec[0]
        params = call_spec[1]
        result_type = call_spec[2] if len(call_spec) > 2 else None
        req_id = _next_id()
        envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "id": req_id}
        if params is not None:
            _encode_params(registry, envelope, params)
        envelopes.append(envelope)
        entries.append((req_id, result_type))
    data = await _post_envelope(registry, envelopes)
    if not isinstance(data, list):
        raise RpcError(SERVER_ERROR, "Malformed batch response")
    by_id: dict[Any, Any] = {}
    for response in data:
        if isinstance(response, dict) and "id" in response:
            by_id[response["id"]] = response
    results: list[Any] = []
    for req_id, result_type in entries:
        response = by_id.get(req_id)
        if response is None:
            raise RpcError(SERVER_ERROR, f"Missing batch response for id {req_id}")
        results.append(_resolve_single(response, result_type, registry))
    return results


__all__ = ["batch", "call", "notify"]
