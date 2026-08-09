from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator, Callable, Iterable
from typing import Any, Generic, TypeVar, cast

from webcompy.aio._aio import aio_run
from webcompy.signal import Signal
from webcompy.signal._composable import _get_active_component_context
from webcompy.signal._graph import consumer_destroy
from webcompy.signal._list import ReactiveList

T = TypeVar("T")


class _StreamQueue(Generic[T]):
    def __init__(self, maxlen: int | None = None) -> None:
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._maxlen = maxlen

    async def get(self) -> T:
        return await self._queue.get()

    def put_nowait(self, item: T) -> None:
        if self._maxlen is not None:
            while self._queue.qsize() >= self._maxlen:
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        self._queue.put_nowait(item)


async def _consume_iterable(
    source: AsyncIterable[T] | Iterable[T],
    on_item: Callable[[T], None],
    on_error: Callable[[Exception], None],
    on_finished: Callable[[], None],
    is_cancelled: Callable[[], bool],
) -> None:
    try:
        if hasattr(source, "__aiter__"):
            async_source = cast("AsyncIterable[T]", source)
            async for item in async_source:
                if is_cancelled():
                    return
                on_item(item)
        else:
            sync_source = cast("Iterable[T]", source)
            for item in sync_source:
                if is_cancelled():
                    return
                on_item(item)
                await asyncio.sleep(0)
        if not is_cancelled():
            on_finished()
    except Exception as err:
        if not is_cancelled():
            on_error(err)


def _register_cleanup(cleanup_fn: Callable[[], None]) -> None:
    ctx = _get_active_component_context()
    if ctx is None:
        return
    from webcompy.components._hooks import on_before_destroy

    previous = ctx.__get_lifecyclehooks__().get("on_before_destroy")
    if previous is None:
        on_before_destroy(cleanup_fn)
        return

    def _combined() -> None:
        cleanup_fn()
        previous()

    on_before_destroy(_combined)


class StreamResult(Generic[T]):
    def __init__(self, initial: T) -> None:
        self._value: Signal[T] = Signal(initial)
        self._error: Signal[Exception | None] = Signal(None)
        self._finished: Signal[bool] = Signal(False)
        self._cancel: Callable[[], None] | None = None

    @property
    def value(self) -> Signal[T]:
        return self._value

    @property
    def error(self) -> Signal[Exception | None]:
        return self._error

    @property
    def finished(self) -> Signal[bool]:
        return self._finished

    def aclose(self) -> None:
        if self._cancel is not None:
            self._cancel()


def to_signal(source: AsyncIterable[T] | Iterable[T], initial: T) -> StreamResult[T]:
    result = StreamResult[T](initial)
    cancelled = False

    def is_cancelled() -> bool:
        return cancelled

    def cancel() -> None:
        nonlocal cancelled
        cancelled = True

    result._cancel = cancel

    def on_item(item: T) -> None:
        result._value.value = item

    def on_error(err: Exception) -> None:
        result._error.value = err
        result._finished.value = True

    def on_finished() -> None:
        result._finished.value = True

    async def _pump() -> None:
        await _consume_iterable(source, on_item, on_error, on_finished, is_cancelled)

    aio_run(_pump())
    _register_cleanup(cancel)
    return result


class StreamListResult(Generic[T]):
    def __init__(self) -> None:
        self._items: ReactiveList[T] = ReactiveList([])
        self._error: Signal[Exception | None] = Signal(None)
        self._finished: Signal[bool] = Signal(False)
        self._cancel: Callable[[], None] | None = None

    @property
    def items(self) -> ReactiveList[T]:
        return self._items

    @property
    def error(self) -> Signal[Exception | None]:
        return self._error

    @property
    def finished(self) -> Signal[bool]:
        return self._finished

    def aclose(self) -> None:
        if self._cancel is not None:
            self._cancel()


def to_reactive_list(
    source: AsyncIterable[T] | Iterable[T],
    *,
    maxlen: int | None = None,
) -> StreamListResult[T]:
    result = StreamListResult[T]()
    cancelled = False

    def is_cancelled() -> bool:
        return cancelled

    def cancel() -> None:
        nonlocal cancelled
        cancelled = True

    result._cancel = cancel

    def on_item(item: T) -> None:
        result._items.append(item)
        if maxlen is not None and len(result._items) > maxlen:
            result._items.pop(0)

    def on_error(err: Exception) -> None:
        result._error.value = err
        result._finished.value = True

    def on_finished() -> None:
        result._finished.value = True

    async def _pump() -> None:
        await _consume_iterable(source, on_item, on_error, on_finished, is_cancelled)

    aio_run(_pump())
    _register_cleanup(cancel)
    return result


def to_async_iter(
    sig: Signal[T],
    *,
    emit_initial: bool = False,
    maxlen: int | None = None,
) -> AsyncIterator[T]:
    queue: _StreamQueue[T] = _StreamQueue(maxlen)
    consumer = sig.on_after_updating(lambda v: queue.put_nowait(v))
    closed = False
    _CLOSED: Any = object()

    def _dispose() -> None:
        nonlocal closed
        if not closed:
            closed = True
            consumer_destroy(consumer)
            queue.put_nowait(_CLOSED)

    _register_cleanup(_dispose)

    async def _generator() -> AsyncGenerator[T, None]:
        try:
            if emit_initial and not closed:
                yield sig.value
            while True:
                item = await queue.get()
                if item is _CLOSED:
                    break
                yield item
        finally:
            _dispose()

    return _generator()
