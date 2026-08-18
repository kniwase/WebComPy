from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from logging import getLogger
from typing import Any

from webcompy.exception import WebComPyException
from webcompy.ports._async_scheduler import AsyncSchedulerPort
from webcompy.utils._environment import ENVIRONMENT

_logger = getLogger(__name__)

_MAX_DRAIN_ITERATIONS = 1000


class BrowserAsyncSchedulerPort(AsyncSchedulerPort):
    def __init__(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserAsyncSchedulerPort is only available in browser environment")
        self._registry: list[tuple[asyncio.Task[Any], bool]] = []

    def schedule(
        self,
        coro: Coroutine[Any, Any, Any],
        *,
        render: bool = False,
    ) -> asyncio.Task[Any]:
        task = asyncio.ensure_future(coro)
        self._registry.append((task, render))
        task.add_done_callback(self._on_done)
        return task

    def _on_done(self, task: asyncio.Task[Any]) -> None:
        for entry in self._registry:
            if entry[0] is task:
                self._registry.remove(entry)
                break

    async def await_pending(self, *, only_render: bool = False) -> None:
        iteration = 0
        while True:
            current = asyncio.current_task()
            pending = [
                task
                for task, render in self._registry
                if task is not current and not task.done() and (render if only_render else True)
            ]
            if not pending:
                break
            await asyncio.gather(*pending, return_exceptions=True)
            iteration += 1
            if iteration > _MAX_DRAIN_ITERATIONS:
                _logger.warning(
                    "BrowserAsyncSchedulerPort.await_pending exceeded %d drain iterations; "
                    "possible recursive scheduling bug (%d tasks still registered)",
                    _MAX_DRAIN_ITERATIONS,
                    len(self._registry),
                )
                break
