from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import Any


class AsyncSchedulerPort(ABC):
    @abstractmethod
    def schedule(
        self,
        coro: Coroutine[Any, Any, Any],
        *,
        render: bool = False,
    ) -> asyncio.Task[Any]:
        """Schedule a coroutine as an ``asyncio.Task``.

        On the browser, this is fire-and-forget; the browser event loop persists
        for the page lifetime so the task completes eventually. On the server,
        the returned task is also registered in an internal per-instance
        registry so that ``await_pending()`` can drain it before the render
        context is disposed.

        Args:
            coro: The coroutine to schedule.
            render: Whether the task is a hydration/render task that must
                complete before the browser hydration reveal (awaitable via
                ``await_pending(only_render=True)``).

        Returns:
            The ``asyncio.Task`` wrapping the scheduled coroutine.

        """
        ...

    @abstractmethod
    async def await_pending(self, *, only_render: bool = False) -> None:
        """Await all currently scheduled tasks.

        Implementations SHALL drain tasks until none remain (handling recursive
        scheduling via a re-check loop) or until a maximum-iteration guard is
        reached. The browser implementation may be a no-op because the event
        loop is long-lived.

        Args:
            only_render: When true, only await tasks scheduled with
                ``schedule(coro, render=True)``. Tasks scheduled without the
                flag SHALL NOT block the call.

        """
        ...
