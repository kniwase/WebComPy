"""Reactive holder for the outcome of an async operation."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from enum import Enum
from typing import Any, Generic, TypeVar

from webcompy.aio._aio import aio_run
from webcompy.signal import Computed, Signal

T = TypeVar("T")
_MISSING: Any = object()


class AsyncState(Enum):
    """Lifecycle stages of an :class:`AsyncResult`.

    ``PENDING`` before the first run, ``LOADING`` while running, and
    ``SUCCESS`` or ``ERROR`` after the operation settles.
    """

    PENDING = "pending"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"


class AsyncResult(Generic[T]):
    """Reactive holder exposing the state and outcome of an async operation.

    The operation function is not launched automatically: call
    :meth:`refetch` to run it. ``state``, ``data``, and ``error`` are
    signals tracking the outcome, and ``is_pending``, ``is_loading``,
    ``is_success``, and ``is_error`` are ``Computed[bool]`` conveniences
    derived from ``state``.

    Args:
        func: Zero-argument coroutine factory producing the value.
        default: Initial value of ``data`` before the first successful run.

    Attributes:
        state: ``Signal[AsyncState]`` holding the current lifecycle state.
        data: ``Signal[T | None]`` holding the latest successfully produced
            value, or ``None`` before the first success.
        error: ``Signal[Exception | None]`` holding the exception from the
            last failed run, or ``None`` after a success.
        is_pending: ``Computed[bool]`` — true while no run has started.
        is_loading: ``Computed[bool]`` — true while a run is in flight.
        is_success: ``Computed[bool]`` — true when the last run succeeded.
        is_error: ``Computed[bool]`` — true when the last run failed.

    """

    def __init__(
        self,
        func: Callable[[], Coroutine[Any, Any, T]],
        default: T | None = _MISSING,
    ) -> None:
        self._func = func
        self._has_default = default is not _MISSING
        self._state: Signal[AsyncState] = Signal(AsyncState.PENDING)
        self._data: Signal[T | None] = Signal(default if default is not _MISSING else None)
        self._error: Signal[Exception | None] = Signal(None)
        self._transferable: bool = True

        self.is_pending: Computed[bool] = Computed(lambda: self._state.value == AsyncState.PENDING)
        self.is_loading: Computed[bool] = Computed(lambda: self._state.value == AsyncState.LOADING)
        self.is_success: Computed[bool] = Computed(lambda: self._state.value == AsyncState.SUCCESS)
        self.is_error: Computed[bool] = Computed(lambda: self._state.value == AsyncState.ERROR)

    @property
    def state(self) -> Signal[AsyncState]:
        """The current :class:`AsyncState`.

        Returns:
            A signal holding the current lifecycle state.

        """
        return self._state

    @property
    def data(self) -> Signal[T | None]:
        """The latest successfully produced value.

        Returns:
            A signal holding the value, or ``None`` before the first success.

        """
        return self._data

    @property
    def error(self) -> Signal[Exception | None]:
        """The exception from the last failed run.

        Returns:
            A signal holding the exception, or ``None`` when the last run succeeded.

        """
        return self._error

    def _restore_from_transfer(self, data: Any) -> None:
        self._state.value = AsyncState.SUCCESS
        self._data.value = data
        self._error.value = None

    def refetch(self, *_: Any) -> None:
        """Run the operation function and move ``state`` to ``LOADING``.

        Args:
            *_: Any positional arguments are ignored; the signature accepts
                them so this method can be wired directly to signal-driven
                callback sites.

        """
        self._state.value = AsyncState.LOADING
        aio_run(self._execute())

    async def _execute(self) -> None:
        try:
            result = await self._func()
            self._data.value = result
            self._state.value = AsyncState.SUCCESS
            self._error.value = None
        except Exception as e:
            self._state.value = AsyncState.ERROR
            self._error.value = e
