from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Literal, Protocol, overload

from webcompy.rpc._errors import SERVER_ERROR, RpcError

if TYPE_CHECKING:
    from webcompy.rpc._stream import RpcStream
    from webcompy.rpc._ws_client import RpcSubscription


class RpcTransport(Protocol):
    async def call(self, method: str, params: Any = None, *, result_type: Any = None) -> Any: ...

    async def notify(self, method: str, params: Any = None) -> None: ...

    def stream(self, method: str, params: Any = None, *, result_type: Any = None) -> Any: ...

    def subscribe(self, method: str, params: Any = None, *, event_type: Any = None) -> Any: ...


def _validate_name(name: str) -> None:
    if not isinstance(name, str) or not name:
        raise TypeError("RPC contract name must be a non-empty str")
    if name.startswith("_webcompy."):
        raise ValueError(f"RPC method name {name!r} is reserved for the framework")


def _validate_type_arg(value: Any, label: str) -> None:
    if not isinstance(value, type):
        raise TypeError(f"{label} must be a type, got {value!r}")


def _validate_params_type(params_type: Any) -> None:
    if not dataclasses.is_dataclass(params_type):
        raise TypeError("params_type must be a dataclass")


class RpcCall[P, R]:
    def __init__(self, name: str, params: P, result_type: type[R], transport: RpcTransport) -> None:
        self._name = name
        self._params = params
        self._result_type: type[R] = result_type
        self._transport = transport
        self._awaited = False

    def __await__(self):  # type: ignore[no-untyped-def]
        if self._awaited:
            raise RuntimeError("RpcCall already awaited")
        self._awaited = True
        return (yield from self._transport.call(self._name, self._params, result_type=self._result_type).__await__())

    def __bool__(self) -> bool:
        raise TypeError("RpcCall has no truth value (did you forget 'await'? Use 'await call' or 'await batch(...)')")

    def __len__(self) -> int:
        raise TypeError("RpcCall has no len()")


class Procedure[P, R]:
    def __init__(self, name: str, params_type: type[P], result_type: type[R]) -> None:
        _validate_name(name)
        _validate_type_arg(params_type, "params_type")
        _validate_type_arg(result_type, "result_type")
        _validate_params_type(params_type)
        self._name = name
        self._params_type: type[P] = params_type
        self._result_type: type[R] = result_type

    @property
    def name(self) -> str:
        return self._name

    @property
    def params_type(self) -> type[P]:
        return self._params_type

    @property
    def result_type(self) -> type[R]:
        return self._result_type

    def __call__(self, transport: RpcTransport, params: P) -> RpcCall[P, R]:
        return RpcCall(self._name, params, self._result_type, transport)


class StreamingProcedure[P, T]:
    def __init__(self, name: str, params_type: type[P], result_type: type[T]) -> None:
        _validate_name(name)
        _validate_type_arg(params_type, "params_type")
        _validate_type_arg(result_type, "result_type")
        _validate_params_type(params_type)
        self._name = name
        self._params_type: type[P] = params_type
        self._result_type: type[T] = result_type

    @property
    def name(self) -> str:
        return self._name

    @property
    def params_type(self) -> type[P]:
        return self._params_type

    @property
    def result_type(self) -> type[T]:
        return self._result_type

    def __call__(self, transport: RpcTransport, params: P) -> RpcStream[T]:
        return transport.stream(self._name, params, result_type=self._result_type)


class Subscription[P, E]:
    def __init__(self, name: str, params_type: type[P], event_type: type[E], replay_size: int = 256) -> None:
        _validate_name(name)
        _validate_type_arg(params_type, "params_type")
        _validate_type_arg(event_type, "event_type")
        _validate_params_type(params_type)
        if isinstance(replay_size, bool) or not isinstance(replay_size, int) or replay_size < 1:
            raise ValueError("replay_size must be an int greater than or equal to 1")
        self._name = name
        self._params_type: type[P] = params_type
        self._event_type: type[E] = event_type
        self._replay_size = replay_size

    @property
    def name(self) -> str:
        return self._name

    @property
    def params_type(self) -> type[P]:
        return self._params_type

    @property
    def event_type(self) -> type[E]:
        return self._event_type

    @property
    def replay_size(self) -> int:
        return self._replay_size

    def __call__(self, transport: RpcTransport, params: P) -> RpcSubscription[E]:
        return transport.subscribe(self._name, params, event_type=self._event_type)


class RpcHttpClient:
    def __init__(self) -> None:
        pass

    async def call(self, method: str, params: Any = None, *, result_type: Any = None) -> Any:
        from webcompy.rpc._client import _call_impl

        return await _call_impl(method, params, result_type=result_type)

    async def notify(self, method: str, params: Any = None) -> None:
        from webcompy.rpc._client import _notify_impl

        await _notify_impl(method, params)

    def stream(self, method: str, params: Any = None, *, result_type: Any = None) -> RpcStream[Any]:
        from webcompy.rpc._client import _stream_impl

        return _stream_impl(method, params, result_type=result_type)

    def subscribe(self, method: str, params: Any = None, *, event_type: Any = None) -> Any:
        raise RpcError(SERVER_ERROR, "subscriptions are WebSocket-only")


_SSR_STREAM_MSG = "webcompy rpc: rpc.stream called outside the browser; returning an empty closed stream"


@overload
async def batch() -> tuple[()]: ...


@overload
async def batch[R1](call1: RpcCall[Any, R1], *, return_exceptions: Literal[False] = False) -> tuple[R1]: ...


@overload
async def batch[R1, R2](
    call1: RpcCall[Any, R1], call2: RpcCall[Any, R2], *, return_exceptions: Literal[False] = False
) -> tuple[R1, R2]: ...


@overload
async def batch[R1, R2, R3](
    call1: RpcCall[Any, R1],
    call2: RpcCall[Any, R2],
    call3: RpcCall[Any, R3],
    *,
    return_exceptions: Literal[False] = False,
) -> tuple[R1, R2, R3]: ...


@overload
async def batch[R1, R2, R3, R4](
    call1: RpcCall[Any, R1],
    call2: RpcCall[Any, R2],
    call3: RpcCall[Any, R3],
    call4: RpcCall[Any, R4],
    *,
    return_exceptions: Literal[False] = False,
) -> tuple[R1, R2, R3, R4]: ...


@overload
async def batch[R1, R2, R3, R4, R5](
    call1: RpcCall[Any, R1],
    call2: RpcCall[Any, R2],
    call3: RpcCall[Any, R3],
    call4: RpcCall[Any, R4],
    call5: RpcCall[Any, R5],
    *,
    return_exceptions: Literal[False] = False,
) -> tuple[R1, R2, R3, R4, R5]: ...


@overload
async def batch[R1, R2, R3, R4, R5, R6](
    call1: RpcCall[Any, R1],
    call2: RpcCall[Any, R2],
    call3: RpcCall[Any, R3],
    call4: RpcCall[Any, R4],
    call5: RpcCall[Any, R5],
    call6: RpcCall[Any, R6],
    *,
    return_exceptions: Literal[False] = False,
) -> tuple[R1, R2, R3, R4, R5, R6]: ...


@overload
async def batch(*calls: RpcCall[Any, Any], return_exceptions: Literal[False] = False) -> tuple[Any, ...]: ...


@overload
async def batch[R1](call1: RpcCall[Any, R1], *, return_exceptions: Literal[True]) -> tuple[R1 | RpcError]: ...


@overload
async def batch[R1, R2](
    call1: RpcCall[Any, R1], call2: RpcCall[Any, R2], *, return_exceptions: Literal[True]
) -> tuple[R1 | RpcError, R2 | RpcError]: ...


@overload
async def batch[R1, R2, R3](
    call1: RpcCall[Any, R1],
    call2: RpcCall[Any, R2],
    call3: RpcCall[Any, R3],
    *,
    return_exceptions: Literal[True],
) -> tuple[R1 | RpcError, R2 | RpcError, R3 | RpcError]: ...


@overload
async def batch[R1, R2, R3, R4](
    call1: RpcCall[Any, R1],
    call2: RpcCall[Any, R2],
    call3: RpcCall[Any, R3],
    call4: RpcCall[Any, R4],
    *,
    return_exceptions: Literal[True],
) -> tuple[R1 | RpcError, R2 | RpcError, R3 | RpcError, R4 | RpcError]: ...


@overload
async def batch[R1, R2, R3, R4, R5](
    call1: RpcCall[Any, R1],
    call2: RpcCall[Any, R2],
    call3: RpcCall[Any, R3],
    call4: RpcCall[Any, R4],
    call5: RpcCall[Any, R5],
    *,
    return_exceptions: Literal[True],
) -> tuple[R1 | RpcError, R2 | RpcError, R3 | RpcError, R4 | RpcError, R5 | RpcError]: ...


@overload
async def batch[R1, R2, R3, R4, R5, R6](
    call1: RpcCall[Any, R1],
    call2: RpcCall[Any, R2],
    call3: RpcCall[Any, R3],
    call4: RpcCall[Any, R4],
    call5: RpcCall[Any, R5],
    call6: RpcCall[Any, R6],
    *,
    return_exceptions: Literal[True],
) -> tuple[R1 | RpcError, R2 | RpcError, R3 | RpcError, R4 | RpcError, R5 | RpcError, R6 | RpcError]: ...


@overload
async def batch(*calls: RpcCall[Any, Any], return_exceptions: Literal[True]) -> tuple[Any | RpcError, ...]: ...


async def batch(*calls: RpcCall[Any, Any], return_exceptions: bool = False) -> tuple[Any, ...]:  # pyright: ignore[reportInconsistentOverload]
    if not calls:
        return ()
    for c in calls:
        if not isinstance(c, RpcCall):
            raise RpcError(SERVER_ERROR, "batch only accepts RpcCall instances")
        if c._awaited:
            raise RuntimeError("RpcCall already awaited")
    transports = {c._transport for c in calls}
    if len(transports) != 1:
        raise RpcError(SERVER_ERROR, "batch requires all calls to share the same transport")
    for c in calls:
        c._awaited = True
    transport = next(iter(transports))
    from webcompy.rpc._client import _encode_params as _http_encode
    from webcompy.rpc._client import _registry_or_error as _reg

    registry = _reg()
    if isinstance(transport, RpcHttpClient):
        envelopes: list[dict[str, Any]] = []
        entries: list[tuple[int, Any]] = []
        for c in calls:
            req_id = registry.next_id()
            envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": c._name, "id": req_id}
            _http_encode(registry, envelope, c._params)
            envelopes.append(envelope)
            entries.append((req_id, c._result_type))
        from webcompy.rpc._client import _post_envelope as _post
        from webcompy.rpc._client import _resolve_single as _resolve

        data = await _post(registry, envelopes)
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
                missing = f"Missing batch response for id {req_id}"
                if return_exceptions:
                    results.append(RpcError(SERVER_ERROR, missing))
                    continue
                raise RpcError(SERVER_ERROR, missing)
            try:
                results.append(_resolve(response, result_type, registry))
            except RpcError as err:
                if return_exceptions:
                    results.append(err)
                else:
                    raise
        return tuple(results)
    from webcompy.rpc._ws_client import RpcWsClient as _Ws

    if isinstance(transport, _Ws):
        return await _ws_batch(transport, calls, return_exceptions)  # type: ignore[arg-type]
    raise RpcError(SERVER_ERROR, "unsupported transport for batch")


async def _ws_batch(transport: Any, calls: tuple[RpcCall[Any, Any], ...], return_exceptions: bool) -> tuple[Any, ...]:
    import asyncio
    import json

    from webcompy.hydration._transfer_meta import encode_with_meta

    registry = transport._registry
    handle = transport._check_usable()
    from webcompy.realtime import ConnectionState as _CS

    if handle.state.value != _CS.OPEN:
        raise RpcError(SERVER_ERROR, "RPC WebSocket connection is not open")
    envelopes: list[dict[str, Any]] = []
    futures: list[tuple[int, Any, asyncio.Future[Any]]] = []
    for c in calls:
        req_id = registry.next_id()
        envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": c._name, "id": req_id}
        json_params, meta = encode_with_meta(c._params, type_handlers=registry.meta_encoders)
        envelope["params"] = json_params
        if meta:
            envelope["meta"] = meta
        envelopes.append(envelope)
        fut: asyncio.Future[Any] = asyncio.Future()
        transport._in_flight[req_id] = fut
        futures.append((req_id, c._result_type, fut))
    handle.send(json.dumps(envelopes))
    results: list[Any] = []
    try:
        for _req_id, result_type, fut in futures:
            try:
                data = await fut
                from webcompy.rpc._client import _resolve_single as _resolve

                results.append(_resolve(data, result_type, registry))
            except RpcError as err:
                if return_exceptions:
                    results.append(err)
                else:
                    raise
            except asyncio.CancelledError:
                raise
            except Exception as err:
                rpc_err = RpcError(SERVER_ERROR, str(err))
                if return_exceptions:
                    results.append(rpc_err)
                else:
                    raise rpc_err from err
    finally:
        for req_id, _, _ in futures:
            transport._in_flight.pop(req_id, None)
    return tuple(results)


@overload
async def notify() -> None: ...


@overload
async def notify(call1: RpcCall[Any, Any]) -> None: ...


@overload
async def notify(call1: RpcCall[Any, Any], call2: RpcCall[Any, Any], *calls: RpcCall[Any, Any]) -> None: ...


async def notify(*calls: RpcCall[Any, Any]) -> None:  # pyright: ignore[reportInconsistentOverload]
    if not calls:
        return None
    for c in calls:
        if not isinstance(c, RpcCall):
            raise RpcError(SERVER_ERROR, "notify only accepts RpcCall instances")
        if c._awaited:
            raise RuntimeError("RpcCall already awaited")
    transports = {c._transport for c in calls}
    if len(transports) != 1:
        raise RpcError(SERVER_ERROR, "notify requires all calls to share the same transport")
    for c in calls:
        c._awaited = True
    transport = next(iter(transports))
    from webcompy.rpc._client import _registry_or_error as _reg

    registry = _reg()
    if isinstance(transport, RpcHttpClient):
        envelopes: list[dict[str, Any]] = []
        for c in calls:
            envelope: dict[str, Any] = {"jsonrpc": "2.0", "method": c._name}
            from webcompy.rpc._client import _encode_params as _http_encode

            _http_encode(registry, envelope, c._params)
            envelopes.append(envelope)
        from webcompy.rpc._client import _post_envelope as _post

        await _post(registry, envelopes)
        return None
    from webcompy.rpc._ws_client import RpcWsClient as _Ws

    if isinstance(transport, _Ws):
        import json

        from webcompy.hydration._transfer_meta import encode_with_meta
        from webcompy.realtime import ConnectionState as _CS

        handle = transport._check_usable()
        if handle.state.value != _CS.OPEN:
            raise RpcError(SERVER_ERROR, "RPC WebSocket connection is not open")
        envelopes = []
        for c in calls:
            envelope = {"jsonrpc": "2.0", "method": c._name}
            json_params, meta = encode_with_meta(c._params, type_handlers=registry.meta_encoders)
            envelope["params"] = json_params
            if meta:
                envelope["meta"] = meta
            envelopes.append(envelope)
        handle.send(json.dumps(envelopes))
        return None
    raise RpcError(SERVER_ERROR, "unsupported transport for notify")


__all__ = [
    "Procedure",
    "RpcCall",
    "RpcHttpClient",
    "RpcTransport",
    "StreamingProcedure",
    "Subscription",
    "batch",
    "notify",
]
