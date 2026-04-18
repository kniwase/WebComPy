from __future__ import annotations

from collections.abc import Callable, Coroutine
from enum import Enum
from typing import Any, Generic, TypeVar

from webcompy.aio._aio import aio_run
from webcompy.signal import Computed, Signal

T = TypeVar("T")
_MISSING: Any = object()


class AsyncState(Enum):
    PENDING = "pending"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"


class AsyncResult(Generic[T]):
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

        self.is_pending: Computed[bool] = Computed(lambda: self._state.value == AsyncState.PENDING)
        self.is_loading: Computed[bool] = Computed(lambda: self._state.value == AsyncState.LOADING)
        self.is_success: Computed[bool] = Computed(lambda: self._state.value == AsyncState.SUCCESS)
        self.is_error: Computed[bool] = Computed(lambda: self._state.value == AsyncState.ERROR)

    @property
    def state(self) -> Signal[AsyncState]:
        return self._state

    @property
    def data(self) -> Signal[T | None]:
        return self._data

    @property
    def error(self) -> Signal[Exception | None]:
        return self._error

    def refetch(self, *_: Any) -> None:
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
