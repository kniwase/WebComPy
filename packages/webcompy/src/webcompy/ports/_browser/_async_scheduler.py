from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

from webcompy.exception import WebComPyException
from webcompy.ports._async_scheduler import AsyncSchedulerPort
from webcompy.utils._environment import ENVIRONMENT


class BrowserAsyncSchedulerPort(AsyncSchedulerPort):
    def __init__(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserAsyncSchedulerPort is only available in browser environment")

    def schedule(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        return asyncio.ensure_future(coro)

    async def await_pending(self) -> None:
        return None
