from typing import Any, Callable, Coroutine, Generic, ParamSpec, TypeVar
from webcompy._browser._modules import browser
from webcompy.reactive._base import ReactiveBase

if browser:
    aio_run: Any = browser.aio.run
else:
    import asyncio

    aio_run: Any = asyncio.run


A = ParamSpec("A")
T = TypeVar("T")


# Async
def resolve_async(
    coroutine: Coroutine[Any, Any, T],
    on_done: Callable[[T], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
):
    async def resolve(
        coroutine: Coroutine[Any, Any, T],
        resolver: Callable[[T], None] | None,
        error: Callable[[Exception], None] | None,
    ) -> None:
        try:
            ret = await coroutine
            if resolver is not None:
                resolver(ret)
        except Exception as err:
            if error is not None:
                error(err)

    aio_run(resolve(coroutine, on_done, on_error))


class AsyncWrapper(Generic[T]):
    def __init__(
        self,
        resolver: Callable[[T], None] = lambda _: None,
        error: Callable[[Exception], None] = lambda _: None,
    ) -> None:
        self.resolver = resolver
        self.error = error

    def __call__(self, async_callable: Callable[A, Coroutine[Any, Any, T]]):
        def inner(*args: A.args, **kwargs: A.kwargs) -> None:
            resolve_async(async_callable(*args, **kwargs), self.resolver, self.error)

        return inner


class AsyncComputed(ReactiveBase[T | None]):
    _done: bool
    _exception: Exception | None

    def __init__(
        self,
        coroutine: Coroutine[Any, Any, T],
    ) -> None:
        super().__init__(None)
        self._done = False
        self._exception = None
        resolve_async(coroutine, self._resolver, self._error)

    @ReactiveBase._change_event
    def _resolver(self, res: T):
        self._done = True
        self._value = res

    @ReactiveBase._change_event
    def _error(self, err: Exception):
        self._done = False
        self._exception = err

    @property
    @ReactiveBase._get_evnet
    def value(self) -> T | None:
        return self._value

    @property
    @ReactiveBase._get_evnet
    def error(self) -> Exception | None:
        return self._exception

    @property
    @ReactiveBase._get_evnet
    def done(self) -> bool:
        return self._done
