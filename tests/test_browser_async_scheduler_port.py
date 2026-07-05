from __future__ import annotations

import asyncio

import pytest

import webcompy.ports._browser._async_scheduler as _browser_module
from webcompy.exception import WebComPyException
from webcompy.ports._browser._async_scheduler import BrowserAsyncSchedulerPort


@pytest.fixture
def browser_scheduler(monkeypatch):
    monkeypatch.setattr(_browser_module, "ENVIRONMENT", "pyscript")
    return BrowserAsyncSchedulerPort()


class TestBrowserAsyncSchedulerPortSchedule:
    @pytest.mark.asyncio
    async def test_schedule_creates_task_via_ensure_future(self, browser_scheduler):
        async def _coro() -> int:
            return 7

        task = browser_scheduler.schedule(_coro())
        assert isinstance(task, asyncio.Task)
        result = await task
        assert result == 7


class TestBrowserAsyncSchedulerPortAwaitPending:
    @pytest.mark.asyncio
    async def test_await_pending_is_noop(self, browser_scheduler):
        await browser_scheduler.await_pending()

        async def _coro() -> None:
            return None

        browser_scheduler.schedule(_coro())
        await browser_scheduler.await_pending()


class TestBrowserAsyncSchedulerPortEnvGuard:
    def test_construct_in_pyscript_env_succeeds(self, monkeypatch):
        monkeypatch.setattr(_browser_module, "ENVIRONMENT", "pyscript")
        BrowserAsyncSchedulerPort()

    def test_construct_outside_pyscript_raises(self, monkeypatch):
        monkeypatch.setattr(_browser_module, "ENVIRONMENT", "server")
        with pytest.raises(WebComPyException):
            BrowserAsyncSchedulerPort()
