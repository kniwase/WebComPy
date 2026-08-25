"""Async execution helpers routed through the framework scheduler."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from re import compile as re_compile
from re import escape as re_escape
from traceback import TracebackException
from typing import Any, Generic, ParamSpec, TypeAlias, TypeVar

from webcompy import logging
from webcompy.utils._environment import ENVIRONMENT

AsyncResolver: TypeAlias = Callable[[Coroutine[Any, Any, Any]], None]


_aio_run_browser_tasks: list[asyncio.Task[Any]] = []


def _schedule_via_port_or_fallback(
    coro: Coroutine[Any, Any, Any],
    fallback: Callable[[Coroutine[Any, Any, Any]], asyncio.Task[Any] | None],
    warning_label: str,
) -> asyncio.Task[Any] | None:
    from webcompy.di import InjectionError, inject
    from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

    try:
        scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
    except InjectionError:
        logging.warning(
            "aio_run called outside render context (%s); task may not be awaited on server",
            warning_label,
        )
        return fallback(coro)
    return scheduler.schedule(coro)


def _aio_run_browser(coro: Coroutine[Any, Any, Any]) -> None:
    def _fallback(c: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        task = asyncio.ensure_future(c)
        _aio_run_browser_tasks.append(task)
        task.add_done_callback(lambda t, _tasks=_aio_run_browser_tasks: _tasks.remove(t) if t in _tasks else None)
        return task

    _schedule_via_port_or_fallback(coro, _fallback, "browser")


def _aio_run_server(coro: Coroutine[Any, Any, Any]) -> None:
    def _fallback(c: Coroutine[Any, Any, Any]) -> asyncio.Task[Any] | None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(c)
            return None
        return loop.create_task(c)

    _schedule_via_port_or_fallback(coro, _fallback, "server")


aio_run: AsyncResolver = _aio_run_browser if ENVIRONMENT == "pyscript" else _aio_run_server


def _aio_run_task(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any] | None:
    """Schedule *coro* like ``aio_run`` but return the created task.

    Unlike the ``aio_run`` fallback, it never blocks on ``asyncio.run``:
    when no event loop is running, ``None`` is returned and the caller
    decides how to proceed. Long-running coroutines (e.g. realtime pumps)
    that must be cancellable shall be scheduled through this helper.
    """

    def _fallback(c: Coroutine[Any, Any, Any]) -> asyncio.Task[Any] | None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return None
        return loop.create_task(c)

    return _schedule_via_port_or_fallback(coro, _fallback, "realtime pump")


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
    """Schedule a coroutine and invoke callbacks when it settles.

    Args:
        coroutine: Coroutine to run.
        on_done: Called with the resolved value when the coroutine succeeds.
        on_error: Called with the exception when the coroutine fails.
            Defaults to logging the error.

    """

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
    """Wrap an async callable to run fire-and-forget when invoked.

    Calling the wrapped callable schedules the produced coroutine through
    ``aio_run`` and resolves it through the configured callbacks.

    Args:
        resolver: Called with the resolved value on success.
        error: Called with the exception on failure. Defaults to logging
            the error.

    Attributes:
        resolver: Success callback invoked with the resolved value, or
            ``None`` when no callback was supplied.
        error: Failure callback invoked with the raised exception.

    """

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


def _resolve_async_callback(callback: Callable[..., Any], value: Any) -> None:
    async def _safe():
        try:
            await callback(value)
        except Exception as err:
            try:
                from webcompy.elements.types._error_boundary import report_unhandled_error

                report_unhandled_error(err)
            except Exception:
                _log_error(err)

    if ENVIRONMENT == "pyscript":
        aio_run(_safe())
    else:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(_safe())
        else:
            import nest_asyncio

            if not getattr(loop, "_nest_asyncio_patched", False):
                nest_asyncio.apply(loop)
                loop._nest_asyncio_patched = True  # type: ignore[attr-defined]
            loop.run_until_complete(_safe())
