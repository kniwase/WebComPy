"""Converters between occurrence-based sources and reactive signals."""

from __future__ import annotations

import asyncio
import weakref
from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator, Callable, Iterable
from typing import Any, Generic, TypeVar, cast

from webcompy.aio._aio import aio_run
from webcompy.signal import ReactiveList, Signal
from webcompy.signal._graph import consumer_destroy

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
    from webcompy.components._hooks import _register_before_destroy_chained

    _register_before_destroy_chained(cleanup_fn)


class StreamResult(Generic[T]):
    """Signals tracking the latest item of a consumed source.

    Args:
        initial: Initial value of the ``value`` signal.

    Attributes:
        value: Signal holding the latest item emitted by the source.
        error: Signal holding the exception that terminated the source,
            or ``None``.
        finished: Signal that becomes ``True`` when the source is
            exhausted (or failed).

    """

    def __init__(self, initial: T) -> None:
        self._value: Signal[T] = Signal(initial)
        self._error: Signal[Exception | None] = Signal(None)
        self._finished: Signal[bool] = Signal(False)
        self._cancel: Callable[[], None] | None = None

    @property
    def value(self) -> Signal[T]:
        """The latest item emitted by the source.

        Returns:
            A signal holding the latest item.

        """
        return self._value

    @property
    def error(self) -> Signal[Exception | None]:
        """The exception that terminated the source, if any.

        Returns:
            A signal holding the exception, or ``None``.

        """
        return self._error

    @property
    def finished(self) -> Signal[bool]:
        """Whether the source finished successfully.

        Returns:
            A signal that becomes ``True`` when the source is exhausted.

        """
        return self._finished

    async def aclose(self) -> None:
        """Cancel consumption of the source and detach the stream handle."""
        if self._cancel is not None:
            self._cancel()


def to_signal(source: AsyncIterable[T] | Iterable[T], initial: T) -> StreamResult[T]:
    """Track the latest item of an async or sync iterable in a signal.

    Consumption starts immediately. Update the returned
    :class:`StreamResult`: ``value`` follows each emitted item, ``error``
    records the terminating exception, and ``finished`` marks exhaustion.
    Call ``aclose()`` to stop consuming.

    Args:
        source: Async or sync iterable whose items are tracked.
        initial: Initial value of the ``value`` signal.

    Returns:
        A :class:`StreamResult` exposing the tracked signals.

    """
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
    """Signals tracking the accumulated items of a consumed source.

    Attributes:
        items: Reactive list that grows as items arrive from the source.
        error: Signal holding the exception that terminated the source,
            or ``None``.
        finished: Signal that becomes ``True`` when the source is
            exhausted (or failed).

    """

    def __init__(self) -> None:
        self._items: ReactiveList[T] = ReactiveList([])
        self._error: Signal[Exception | None] = Signal(None)
        self._finished: Signal[bool] = Signal(False)
        self._cancel: Callable[[], None] | None = None

    @property
    def items(self) -> ReactiveList[T]:
        """The items accumulated from the source so far.

        Returns:
            A reactive list that grows as items arrive.

        """
        return self._items

    @property
    def error(self) -> Signal[Exception | None]:
        """The exception that terminated the source, if any.

        Returns:
            A signal holding the exception, or ``None``.

        """
        return self._error

    @property
    def finished(self) -> Signal[bool]:
        """Whether the source finished successfully.

        Returns:
            A signal that becomes ``True`` when the source is exhausted.

        """
        return self._finished

    async def aclose(self) -> None:
        """Cancel consumption of the source and detach the stream handle."""
        if self._cancel is not None:
            self._cancel()


def to_reactive_list(
    source: AsyncIterable[T] | Iterable[T],
    *,
    maxlen: int | None = None,
) -> StreamListResult[T]:
    """Append the items of an async or sync iterable to a reactive list.

    Consumption starts immediately. Items are appended to ``items`` in
    arrival order until the source finishes; call ``aclose()`` to stop
    consuming.

    Args:
        source: Async or sync iterable whose items are collected.
        maxlen: When given, drop the oldest items so the list never grows
            beyond this length.

    Returns:
        A :class:`StreamListResult` exposing the accumulated items.

    """
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


class StreamAsyncIterator(Generic[T]):
    """An async iterator that disposes its generator source on close.

    Args:
        generator: Async generator yielding the iterator's items.
        dispose: Cleanup callback invoked exactly once, when the iterator
            is closed or garbage collected.

    """

    def __init__(
        self,
        generator: AsyncGenerator[T, None],
        dispose: Callable[[], None],
    ) -> None:
        self._generator = generator
        self._dispose = dispose
        # retain the finalizer handle so the cleanup callback stays alive for the iterator's lifetime
        self._finalizer = weakref.finalize(self, dispose)

    def __aiter__(self) -> AsyncIterator[T]:
        return self

    async def __anext__(self) -> T:
        return await self._generator.__anext__()

    async def aclose(self) -> None:
        """Dispose the source generator and close the iterator."""
        self._dispose()
        await self._generator.aclose()


def to_async_iter(
    sig: Signal[T],
    *,
    emit_initial: bool = False,
    maxlen: int | None = None,
) -> StreamAsyncIterator[T]:
    """Convert the updates of a signal into an async iterator.

    Yields each new value of ``sig`` as an occurrence. Queueing is
    drop-oldest: while the consumer falls behind, older values are dropped
    so the next yield is always the newest available value. The iterator
    stops when closed or when the surrounding component is destroyed.

    Args:
        sig: The signal whose updated values are yielded.
        emit_initial: When ``True``, yield the current value first.
        maxlen: Optional bound on the queue of pending values.

    Returns:
        A :class:`StreamAsyncIterator` yielding the signal's updated values.

    """
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

    return StreamAsyncIterator(_generator(), _dispose)
