from __future__ import annotations

import asyncio

import pytest

from webcompy_testing._ports import FakeAsyncSchedulerPort


class TestFakeAsyncSchedulerPort:
    @pytest.mark.asyncio
    async def test_schedule_collects_coroutines_without_executing(self):
        scheduler = FakeAsyncSchedulerPort()
        executed: list[int] = []

        async def _coro() -> None:
            executed.append(1)

        scheduler.schedule(_coro())
        assert len(scheduler._coroutines) == 1
        await asyncio.sleep(0)
        assert executed == []

    @pytest.mark.asyncio
    async def test_drain_executes_collected_coroutines(self):
        scheduler = FakeAsyncSchedulerPort()
        executed: list[int] = []

        async def _make_coro(value: int):
            await asyncio.sleep(0)
            executed.append(value)

        scheduler.schedule(_make_coro(10))
        scheduler.schedule(_make_coro(20))
        scheduler.schedule(_make_coro(30))

        await scheduler.drain()
        assert sorted(executed) == [10, 20, 30]
        assert scheduler._coroutines == []

    @pytest.mark.asyncio
    async def test_await_pending_delegates_to_drain(self):
        scheduler = FakeAsyncSchedulerPort()
        executed: list[int] = []

        async def _make_coro(value: int):
            executed.append(value)

        scheduler.schedule(_make_coro(1))
        scheduler.schedule(_make_coro(2))
        await scheduler.await_pending()
        assert sorted(executed) == [1, 2]
        assert scheduler._coroutines == []
