from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from re import compile as re_compile
from re import escape as re_escape
from traceback import TracebackException
from typing import Any, Generic, ParamSpec, TypeAlias, TypeVar

from webcompy import logging
from webcompy._browser._modules import browser

AsyncResolver: TypeAlias = Callable[[Coroutine[Any, Any, Any]], None]


def _aio_run_browser(coro: Coroutine[Any, Any, Any]) -> None:
    task = asyncio.ensure_future(coro)
    _aio_run_browser_tasks.append(task)
    task.add_done_callback(lambda t: _aio_run_browser_tasks.remove(t))


_aio_run_browser_tasks: list[asyncio.Task[Any]] = []


aio_run: AsyncResolver = _aio_run_browser if browser else asyncio.run


A = ParamSpec("A")
T = TypeVar("T")


_package_name = "/webcompy/"
_filepath_in_package = _package_name + __file__.split(_package_name)[-1]
_is_traceback_in_this_file = re_compile(
    r'\s+File\s+".+' + re_escape(_filepath_in_package) + r'",\s+line\s+[0-9]+,\s+in\s+'
).match


def _log_error(error: Exception):
    logging.error(
        "".join(row for row in TracebackException.from_exception(error).format() if not _is_traceback_in_this_file(row))
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
