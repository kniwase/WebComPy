from __future__ import annotations
from traceback import TracebackException
from re import compile as re_complie, escape as re_escape
from typing import Any, Callable, Coroutine, Generic, TypeVar, Union
from typing_extensions import ParamSpec, TypeAlias
from webcompy._browser._modules import browser
from webcompy.reactive._base import ReactiveBase
from webcompy import logging

AsysncResolver: TypeAlias = Callable[[Coroutine[Any, Any, Any]], None]

if browser:
    aio_run: AsysncResolver = (
        browser.pyodide.webloop.WebLoop().run_until_complete
    )
else:
    import asyncio

    aio_run: AsysncResolver = asyncio.run


A = ParamSpec("A")
T = TypeVar("T")


_package_name = "/webcompy/"
_filepath_in_package = _package_name + __file__.split(_package_name)[-1]
_is_traceback_in_this_file = re_complie(
    r'\s+File\s+".+' + re_escape(_filepath_in_package) + r'",\s+line\s+[0-9]+,\s+in\s+'
).match


def _log_error(error: Exception):
    logging.error(
        "".join(
            row
            for row in TracebackException.from_exception(error).format()
            if not _is_traceback_in_this_file(row)
        )
    )


# Async
def resolve_async(
    coroutine: Coroutine[Any, Any, T],
    on_done: Callable[[T], Any] | None = None,
    on_error: Callable[[Exception], Any] | None = _log_error,
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
        resolver: Callable[[T], Any] | None = None,
        error: Callable[[Exception], Any] | None = _log_error,
    ) -> None:
        self.resolver = resolver
        self.error = error

    def __call__(self, async_callable: Callable[A, Coroutine[Any, Any, T]]):
        def inner(*args: A.args, **kwargs: A.kwargs) -> None:
            resolve_async(async_callable(*args, **kwargs), self.resolver, self.error)

        return inner


class AsyncComputed(ReactiveBase[Union[T, None]]):
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
