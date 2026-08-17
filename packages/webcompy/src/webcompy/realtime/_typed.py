from __future__ import annotations

import json
import warnings
from collections.abc import AsyncIterator, Callable, Mapping
from typing import Any, Generic, TypeVar

from webcompy.ajax import from_json
from webcompy.di._keys import _REALTIME_TYPE_REGISTRY_KEY
from webcompy.di._scope import _get_app_di_scope
from webcompy.hydration._transfer_meta import (
    META_BODY_KEY,
    _qualified_type_name,
    apply_transfer_meta,
    encode_with_meta,
    merge_meta_into_body,
)
from webcompy.realtime._registry import CloseInfo, ConnectionState
from webcompy.realtime._ws import WebSocketHandle
from webcompy.signal import Signal

T = TypeVar("T")

_NO_SCOPE_MSG = (
    "webcompy realtime: register_realtime_type_handler called with no app DI scope; the registration is a no-op"
)
_SKIP_MSG = "webcompy realtime: received an invalid typed WebSocket frame; skipping it"


class _RealtimeTypeRegistry:
    def __init__(self) -> None:
        self._meta_encoders: dict[type, tuple[str, Callable[[Any], Any]]] = {}
        self._meta_decoders: dict[str, Callable[[Any], Any]] = {}

    def register(
        self,
        cls: type,
        encoder: Callable[[Any], Any],
        decoder: Callable[[Any], Any],
    ) -> None:
        tag = _qualified_type_name(cls)
        self._meta_encoders[cls] = (tag, encoder)
        self._meta_decoders[tag] = decoder

    @property
    def meta_encoders(self) -> dict[type, tuple[str, Callable[[Any], Any]]]:
        return self._meta_encoders

    @property
    def meta_decoders(self) -> dict[str, Callable[[Any], Any]]:
        return self._meta_decoders


def _get_or_create_type_registry() -> _RealtimeTypeRegistry | None:
    scope = _get_app_di_scope()
    if scope is None:
        return None
    existing = scope.inject(_REALTIME_TYPE_REGISTRY_KEY, default=None)
    if existing is None:
        existing = _RealtimeTypeRegistry()
        scope.provide(_REALTIME_TYPE_REGISTRY_KEY, existing)
    return existing


def register_realtime_type_handler(
    cls: type,
    encoder: Callable[[Any], Any],
    decoder: Callable[[Any], Any],
) -> None:
    """Register a custom type for typed realtime messages in the app DI scope.

    The encoder converts an instance to a JSON-serializable value and the
    decoder restores it. Tags use the qualified type name; only builtin tags
    and registered tags are accepted on receive. Outside an app DI scope the
    registration is a no-op and a ``UserWarning`` is emitted.
    """
    registry = _get_or_create_type_registry()
    if registry is None:
        warnings.warn(_NO_SCOPE_MSG, UserWarning, stacklevel=2)
        return
    registry.register(cls, encoder, decoder)


def _encode_frame(instance: Any, registry: _RealtimeTypeRegistry | None) -> str:
    type_handlers = registry.meta_encoders if registry is not None else None
    json_data, meta = encode_with_meta(instance, type_handlers=type_handlers)
    return json.dumps(merge_meta_into_body(json_data, meta))


def _decode_frame(
    text: str,
    message_type: type[T],
    *,
    strict: bool,
    registry: _RealtimeTypeRegistry | None,
) -> T:
    data = json.loads(text)
    meta: Mapping[str, str] | None = None
    if isinstance(data, dict):
        meta_value = data.pop(META_BODY_KEY, None)
        if meta_value is not None:
            meta = meta_value
    if meta is not None:
        data = apply_transfer_meta(
            data, meta, strict=True, decoders=registry.meta_decoders if registry is not None else None
        )
    return from_json(message_type, data, strict=strict)


class TypedWebSocketHandle(Generic[T]):
    def __init__(
        self,
        raw: WebSocketHandle,
        message_type: type[T],
        *,
        strict: bool,
        registry: _RealtimeTypeRegistry | None,
    ) -> None:
        self._raw = raw
        self._message_type = message_type
        self._strict = strict
        self._registry = registry
        self._last_error: Signal[Exception | None] = Signal(None)

    @property
    def state(self) -> Signal[ConnectionState]:
        return self._raw.state

    @property
    def last_close(self) -> Signal[CloseInfo | None]:
        return self._raw.last_close

    @property
    def last_error(self) -> Signal[Exception | None]:
        return self._last_error

    def send(self, message: T) -> None:
        self._raw.send(_encode_frame(message, self._registry))

    def close(self) -> None:
        self._raw.close()

    def __aiter__(self) -> AsyncIterator[T]:
        return self

    async def __anext__(self) -> T:
        while True:
            text = await self._raw.__anext__()
            try:
                instance = _decode_frame(text, self._message_type, strict=self._strict, registry=self._registry)
            except (ValueError, TypeError) as err:
                self._last_error.value = err
                warnings.warn(f"{_SKIP_MSG}: {err}", UserWarning, stacklevel=2)
                continue
            self._last_error.value = None
            return instance
