"""Client-side typed RPC streams with lifecycle states."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

from webcompy.ajax._serde import from_json
from webcompy.hydration._transfer_meta import apply_transfer_meta
from webcompy.rpc._errors import INTERNAL_ERROR, SERVER_ERROR, RpcError
from webcompy.rpc._registry import ProcedureRegistry
from webcompy.signal import Signal

STREAM_DONE_METHOD = "_webcompy.stream_done"
STREAM_ERROR_METHOD = "_webcompy.stream_error"
STREAM_CANCEL_METHOD = "_webcompy.stream_cancel"

T = TypeVar("T")

_STOP: Any = object()


@dataclass(frozen=True)
class _Failure:
    error: RpcError


def _decode_stream_item(data: Any, meta: Any, result_type: Any, registry: ProcedureRegistry) -> Any:
    """Decode one stream item with the same typed codec as ordinary RPC results."""
    if meta is not None:
        if not isinstance(meta, Mapping):
            raise RpcError(SERVER_ERROR, "Malformed RPC stream item meta")
        try:
            data = apply_transfer_meta(data, meta, strict=False, decoders=registry.meta_decoders)
        except ValueError as err:
            raise RpcError(INTERNAL_ERROR, f"Failed to apply stream item meta: {err}") from err
    if result_type is None:
        return data
    try:
        return from_json(result_type, data)
    except (TypeError, ValueError) as err:
        raise RpcError(INTERNAL_ERROR, f"RPC stream item does not match schema: {err}") from err


class RpcStreamState(Enum):
    """Lifecycle stages of an :class:`RpcStream`.

    ``OPEN`` while active, ``CLOSED`` after normal exhaustion or explicit
    closure, and ``FAILED`` when the stream failed.
    """

    OPEN = "open"
    CLOSED = "closed"
    FAILED = "failed"


class RpcStream(Generic[T]):
    """An async iterator over a finite, call-scoped RPC stream.

    ``.state`` is a ``Signal[RpcStreamState]``: ``OPEN`` while the stream is
    active, ``CLOSED`` after normal exhaustion or explicit close, and
    ``FAILED`` when the stream failed. ``.close()`` is idempotent, terminates
    the stream, and cancels the underlying transport. Streams created inside
    component setup are closed automatically on component destroy.

    Args:
        cancel: Optional callback cancelling the underlying transport.
        decode: Optional two-argument function decoding each raw item.
        closed: When ``True``, the stream starts already closed.

    Attributes:
        state: ``Signal[RpcStreamState]`` — ``OPEN`` while active,
            ``CLOSED`` after normal exhaustion or explicit close, and
            ``FAILED`` when the stream failed.

    """

    def __init__(
        self,
        *,
        cancel: Callable[[], None] | None = None,
        decode: Callable[[Any, Any], T] | None = None,
        closed: bool = False,
    ) -> None:
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._cancel = cancel
        self._decode = decode or (lambda data, _meta: data)
        self._finished = closed
        self._done = closed
        self.state: Signal[RpcStreamState] = Signal(RpcStreamState.CLOSED if closed else RpcStreamState.OPEN)
        if closed:
            self._queue.put_nowait(_STOP)
        else:
            from webcompy.components._hooks import _register_before_destroy_chained

            _register_before_destroy_chained(self.close)

    def __aiter__(self) -> RpcStream[T]:
        return self

    async def __anext__(self) -> T:
        if self._done:
            raise StopAsyncIteration
        item = await self._queue.get()
        if item is _STOP or self._done:
            self._done = True
            raise StopAsyncIteration
        if isinstance(item, _Failure):
            self._done = True
            raise item.error
        return item

    def close(self) -> None:
        """Terminate the stream and cancel the underlying transport.

        Idempotent: closing an already closed stream is a no-op.
        """
        if self._done:
            return
        self._done = True
        self._finished = True
        if self.state.value == RpcStreamState.OPEN:
            self.state.value = RpcStreamState.CLOSED
        cancel, self._cancel = self._cancel, None
        if cancel is not None:
            cancel()
        self._queue.put_nowait(_STOP)

    def _deliver(self, item: T) -> None:
        if not self._finished:
            self._queue.put_nowait(item)

    def _deliver_raw(self, data: Any, meta: Any) -> None:
        if self._finished:
            return
        try:
            self._deliver(self._decode(data, meta))
        except RpcError as err:
            self._fail(err)

    def _finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._cancel = None
        self.state.value = RpcStreamState.CLOSED
        self._queue.put_nowait(_STOP)

    def _fail(self, error: RpcError) -> None:
        if self._finished:
            return
        self._finished = True
        self._cancel = None
        self.state.value = RpcStreamState.FAILED
        self._queue.put_nowait(_Failure(error))

    async def __aenter__(self) -> RpcStream[T]:
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        self.close()


__all__ = [
    "STREAM_CANCEL_METHOD",
    "STREAM_DONE_METHOD",
    "STREAM_ERROR_METHOD",
    "RpcStream",
    "RpcStreamState",
]
