"""Server-side async scheduler port."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

from webcompy.ports._async_scheduler import AsyncSchedulerPort

_logger = logging.getLogger(__name__)

_MAX_DRAIN_ITERATIONS = 20


class ServerAsyncSchedulerPort(AsyncSchedulerPort):
    """Server-side async task scheduler for SSR.

    Tracks scheduled tasks and drains them during ``await_pending``.
    """

    def __init__(self) -> None:
        self._registry: list[asyncio.Task[Any]] = []

    def schedule(
        self,
        coro: Coroutine[Any, Any, Any],
        *,
        render: bool = False,
    ) -> asyncio.Task[Any]:
        """Schedule a coroutine for execution.

        Args:
            coro: Coroutine to schedule.
            render: Whether the task is render-scoped.

        Returns:
            Created ``asyncio.Task``.

        """
        loop = asyncio.get_running_loop()
        task = loop.create_task(coro)
        self._registry.append(task)
        task.add_done_callback(self._on_done)
        return task

    def _on_done(self, task: asyncio.Task[Any]) -> None:
        if task in self._registry:
            self._registry.remove(task)

    async def await_pending(self, *, only_render: bool = False) -> None:
        """Wait for pending scheduled tasks to complete.

        Args:
            only_render: If ``True``, wait only for render-scoped tasks.

        Returns:
            ``None``.

        """
        iteration = 0
        while self._registry:
            tasks = list(self._registry)
            await asyncio.gather(*tasks, return_exceptions=True)
            iteration += 1
            if iteration > _MAX_DRAIN_ITERATIONS:
                _logger.warning(
                    "ServerAsyncSchedulerPort.await_pending exceeded %d drain iterations; "
                    "possible recursive scheduling bug (%d tasks still registered)",
                    _MAX_DRAIN_ITERATIONS,
                    len(self._registry),
                )
                break
