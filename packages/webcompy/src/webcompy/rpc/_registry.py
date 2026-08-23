from __future__ import annotations

import collections.abc
import inspect
import itertools
import typing
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from webcompy.exception import WebComPyException
from webcompy.hydration._transfer_meta import BUILTIN_META_TAGS, _qualified_type_name

DEFAULT_RPC_PATH = "/_webcompy-rpc"


@dataclass(frozen=True)
class ProcedureInfo:
    name: str
    func: Callable[..., Any]
    param_schemas: dict[str, Any]
    param_order: list[str]
    required: frozenset[str]
    result_schema: Any
    is_async: bool
    is_streaming: bool


@dataclass(frozen=True)
class SubscriptionInfo:
    name: str
    func: Callable[..., Any]
    param_schemas: dict[str, Any]
    param_order: list[str]
    required: frozenset[str]
    replay_size: int


def _extract_signature(name: str, func: Callable[..., Any]) -> tuple[dict[str, Any], list[str], frozenset[str], Any]:
    try:
        hints = typing.get_type_hints(func)
    except Exception as err:
        raise WebComPyException(f"RPC procedure {name!r}: failed to resolve type hints: {err}") from err
    signature = inspect.signature(func)
    param_schemas: dict[str, Any] = {}
    param_order: list[str] = []
    untyped: list[str] = []
    for param_name, param in signature.parameters.items():
        if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            raise WebComPyException(f"RPC procedure {name!r}: variadic parameter {param_name!r} is not allowed")
        if param_name not in hints:
            untyped.append(param_name)
            continue
        param_schemas[param_name] = hints[param_name]
        param_order.append(param_name)
    if untyped:
        raise WebComPyException(f"RPC procedure {name!r}: untyped parameter(s): {', '.join(untyped)}")
    required = frozenset(
        param_name for param_name, param in signature.parameters.items() if param.default is inspect.Parameter.empty
    )
    return param_schemas, param_order, required, hints.get("return")


_STREAM_ORIGINS = (
    collections.abc.AsyncIterator,
    collections.abc.AsyncIterable,
    collections.abc.Iterator,
    collections.abc.Iterable,
)
_ASYNC_STREAM_ORIGINS = (collections.abc.AsyncIterator, collections.abc.AsyncIterable)


def _resolve_streaming(name: str, func: Callable[..., Any], result_schema: Any) -> tuple[bool, Any]:
    """Resolve whether ``func`` is a streaming procedure and its element schema.

    A generator function whose return annotation is a subscripted
    ``AsyncIterator[T]`` / ``AsyncIterable[T]`` (async generator) or
    ``Iterator[T]`` / ``Iterable[T]`` (sync generator) registers as streaming
    with element schema ``T``. Returns ``(is_streaming, result_schema)`` where
    ``result_schema`` is the element type for streaming procedures and
    unchanged otherwise.
    """
    is_async_gen = inspect.isasyncgenfunction(func)
    is_sync_gen = inspect.isgeneratorfunction(func)
    origin = typing.get_origin(result_schema)
    if origin in _STREAM_ORIGINS:
        args = typing.get_args(result_schema)
        if not args:
            raise WebComPyException(
                f"RPC procedure {name!r}: streaming return annotation requires an element type (e.g. AsyncIterator[T])"
            )
        is_async_annotation = origin in _ASYNC_STREAM_ORIGINS
        if is_async_gen and not is_async_annotation:
            raise WebComPyException(
                f"RPC procedure {name!r}: async generator function must be annotated with "
                "AsyncIterator[T] or AsyncIterable[T]"
            )
        if is_sync_gen and is_async_annotation:
            raise WebComPyException(
                f"RPC procedure {name!r}: sync generator function must be annotated with Iterator[T] or Iterable[T]"
            )
        if not (is_async_gen or is_sync_gen):
            raise WebComPyException(
                f"RPC procedure {name!r}: streaming return annotation requires a generator function"
            )
        return True, args[0]
    if any(result_schema is stream_origin for stream_origin in _STREAM_ORIGINS):
        raise WebComPyException(
            f"RPC procedure {name!r}: streaming return annotation {result_schema!r} requires an element type "
            "(e.g. AsyncIterator[T])"
        )
    if is_async_gen or is_sync_gen:
        raise WebComPyException(
            f"RPC procedure {name!r}: generator functions must declare an iterable return annotation "
            "(e.g. AsyncIterator[T] for async generators, Iterator[T] for sync generators)"
        )
    return False, result_schema


class ProcedureRegistry:
    def __init__(self, *, base_url: str = "/") -> None:
        self._path = DEFAULT_RPC_PATH
        self._base_url = base_url
        self._procedures: dict[str, ProcedureInfo] = {}
        self._subscriptions: dict[str, SubscriptionInfo] = {}
        self._type_handlers: dict[str, tuple[type, Callable[[Any], Any], Callable[[Any], Any]]] = {}
        self._meta_encoders: dict[type, tuple[str, Callable[[Any], Any]]] = {}
        self._meta_decoders: dict[str, Callable[[Any], Any]] = {}
        self._id_counter = itertools.count(1)

    @property
    def path(self) -> str:
        return self._path

    @property
    def endpoint_url(self) -> str:
        if self._base_url == "/":
            return self._path
        return self._base_url.rstrip("/") + self._path

    def set_path(self, path: str) -> None:
        if not path.startswith("/") or path == "/":
            raise WebComPyException(f"RPC path must be an absolute non-root path, got {path!r}")
        self._path = path

    @property
    def has_procedures(self) -> bool:
        return bool(self._procedures or self._subscriptions)

    def next_id(self) -> int:
        return next(self._id_counter)

    def get(self, name: str) -> ProcedureInfo | None:
        return self._procedures.get(name)

    def get_subscription(self, name: str) -> SubscriptionInfo | None:
        return self._subscriptions.get(name)

    def _validate_name(self, name: str) -> None:
        if name.startswith("_webcompy."):
            raise WebComPyException(f"RPC method name {name!r} is reserved for the framework")

    def bind(self, contract: Any, impl: Callable[..., Any] | None = None) -> Any:
        from webcompy.rpc._contracts import Procedure, StreamingProcedure, Subscription

        if impl is None:

            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                self.bind(contract, fn)
                return fn

            return decorator
        if isinstance(contract, Procedure):
            name = contract.name
            self._validate_name(name)
            if name in self._procedures or name in self._subscriptions:
                raise WebComPyException(f"RPC procedure {name!r} is already registered")
            if inspect.isgeneratorfunction(impl) or inspect.isasyncgenfunction(impl):
                raise WebComPyException(
                    f"RPC procedure {name!r}: generator functions must be bound to StreamingProcedure"
                )
            param_schemas, param_order, required, result_schema = _extract_signature(name, impl)
            if result_schema is None:
                raise WebComPyException(f"RPC procedure {name!r}: missing return type annotation")
            if len(param_order) != 1:
                raise WebComPyException(
                    f"RPC procedure {name!r}: expected exactly one parameter of type {contract.params_type!r}, got {len(param_order)}"
                )
            param_type = param_schemas[param_order[0]]
            if param_type != contract.params_type:
                raise WebComPyException(
                    f"RPC procedure {name!r}: parameter type mismatch: expected {contract.params_type!r}, got {param_type!r}"
                )
            if result_schema != contract.result_type:
                raise WebComPyException(
                    f"RPC procedure {name!r}: return type mismatch: expected {contract.result_type!r}, got {result_schema!r}"
                )
            origin = typing.get_origin(result_schema)
            if origin in _STREAM_ORIGINS:
                raise WebComPyException(
                    f"RPC procedure {name!r}: streaming return annotation requires a generator function (use StreamingProcedure)"
                )
            if result_schema in _STREAM_ORIGINS:
                raise WebComPyException(f"RPC procedure {name!r}: streaming return annotation requires an element type")
            self._procedures[name] = ProcedureInfo(
                name=name,
                func=impl,
                param_schemas=param_schemas,
                param_order=param_order,
                required=required,
                result_schema=result_schema,
                is_async=inspect.iscoroutinefunction(impl),
                is_streaming=False,
            )
            return None
        if isinstance(contract, StreamingProcedure):
            name = contract.name
            self._validate_name(name)
            if name in self._procedures or name in self._subscriptions:
                raise WebComPyException(f"RPC procedure {name!r} is already registered")
            param_schemas, param_order, required, result_schema = _extract_signature(name, impl)
            if result_schema is None:
                raise WebComPyException(f"RPC procedure {name!r}: missing return type annotation")
            if len(param_order) != 1:
                raise WebComPyException(
                    f"RPC procedure {name!r}: expected exactly one parameter of type {contract.params_type!r}"
                )
            param_type = param_schemas[param_order[0]]
            if param_type != contract.params_type:
                raise WebComPyException(
                    f"RPC procedure {name!r}: parameter type mismatch: expected {contract.params_type!r}, got {param_type!r}"
                )
            is_streaming, element = _resolve_streaming(name, impl, result_schema)
            if not is_streaming:
                raise WebComPyException(
                    f"RPC procedure {name!r}: StreamingProcedure requires a generator function with iterable return annotation"
                )
            if element != contract.result_type:
                raise WebComPyException(
                    f"RPC procedure {name!r}: element type mismatch: expected {contract.result_type!r}, got {element!r}"
                )
            self._procedures[name] = ProcedureInfo(
                name=name,
                func=impl,
                param_schemas=param_schemas,
                param_order=param_order,
                required=required,
                result_schema=element,
                is_async=inspect.isasyncgenfunction(impl),
                is_streaming=True,
            )
            return None
        if isinstance(contract, Subscription):
            name = contract.name
            self._validate_name(name)
            if name in self._procedures or name in self._subscriptions:
                raise WebComPyException(f"RPC subscription {name!r} is already registered")
            if not inspect.isasyncgenfunction(impl):
                raise WebComPyException(f"RPC subscription {name!r} must be an async generator function")
            param_schemas, param_order, required, result_schema = _extract_signature(name, impl)
            if result_schema is None:
                raise WebComPyException(f"RPC subscription {name!r}: missing return type annotation")
            if len(param_order) != 1:
                raise WebComPyException(
                    f"RPC subscription {name!r}: expected exactly one parameter of type {contract.params_type!r}"
                )
            param_type = param_schemas[param_order[0]]
            if param_type != contract.params_type:
                raise WebComPyException(
                    f"RPC subscription {name!r}: parameter type mismatch: expected {contract.params_type!r}, got {param_type!r}"
                )
            origin = typing.get_origin(result_schema)
            args = typing.get_args(result_schema)
            if origin not in (collections.abc.AsyncIterator, collections.abc.AsyncGenerator):
                raise WebComPyException(
                    f"RPC subscription {name!r}: return annotation must be AsyncIterator[T] or AsyncGenerator[T, None]"
                )
            if not args:
                raise WebComPyException(f"RPC subscription {name!r}: missing element type (e.g. AsyncIterator[T])")
            element = args[0]
            if element is object or element is Any:
                raise WebComPyException(
                    f"RPC subscription {name!r}: element type must be a concrete type, got {element!r}"
                )
            if element != contract.event_type:
                raise WebComPyException(
                    f"RPC subscription {name!r}: element type mismatch: expected {contract.event_type!r}, got {element!r}"
                )
            if origin is collections.abc.AsyncGenerator and len(args) == 2 and args[1] is not type(None):
                raise WebComPyException(f"RPC subscription {name!r}: AsyncGenerator second arg must be None")
            self._subscriptions[name] = SubscriptionInfo(
                name=name,
                func=impl,
                param_schemas=param_schemas,
                param_order=param_order,
                required=required,
                replay_size=contract.replay_size,
            )
            return None
        raise TypeError(f"bind expects Procedure, StreamingProcedure or Subscription, got {type(contract)!r}")

    def register_type_handler(
        self,
        cls: type,
        encoder: Callable[[Any], Any],
        decoder: Callable[[Any], Any],
    ) -> None:
        tag = _qualified_type_name(cls)
        self._type_handlers[tag] = (cls, encoder, decoder)
        self._meta_encoders[cls] = (tag, encoder)
        self._meta_decoders[tag] = decoder

    @property
    def meta_encoders(self) -> dict[type, tuple[str, Callable[[Any], Any]]]:
        return self._meta_encoders

    @property
    def meta_decoders(self) -> dict[str, Callable[[Any], Any]]:
        return self._meta_decoders

    def is_known_meta_tag(self, tag: str) -> bool:
        return tag in BUILTIN_META_TAGS or tag in self._type_handlers


__all__ = [
    "DEFAULT_RPC_PATH",
    "ProcedureInfo",
    "ProcedureRegistry",
    "SubscriptionInfo",
]
