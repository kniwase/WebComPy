from __future__ import annotations

import asyncio

import pytest

from webcompy_server.ports._async_scheduler import ServerAsyncSchedulerPort


class TestServerAsyncSchedulerPortSchedule:
    @pytest.mark.asyncio
    async def test_schedule_registers_task_in_registry(self):
        scheduler = ServerAsyncSchedulerPort()
        assert scheduler._registry == []

        async def _coro() -> int:
            return 42

        task = scheduler.schedule(_coro())
        assert task in scheduler._registry
        assert len(scheduler._registry) == 1


class TestServerAsyncSchedulerPortAwaitPending:
    @pytest.mark.asyncio
    async def test_drains_all_pending_tasks_and_leaves_registry_empty(self):
        scheduler = ServerAsyncSchedulerPort()
        results: list[int] = []

        async def _make_coro(value: int):
            await asyncio.sleep(0)
            results.append(value)

        scheduler.schedule(_make_coro(1))
        scheduler.schedule(_make_coro(2))
        scheduler.schedule(_make_coro(3))
        assert len(scheduler._registry) == 3

        await scheduler.await_pending()
        assert scheduler._registry == []
        assert sorted(results) == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_drain_loop_handles_recursive_scheduling(self):
        scheduler = ServerAsyncSchedulerPort()
        executed: list[int] = []

        async def _recursive_spawn(value: int, max_depth: int):
            executed.append(value)
            if value < max_depth:
                scheduler.schedule(_recursive_spawn(value + 1, max_depth))

        scheduler.schedule(_recursive_spawn(1, 4))
        await scheduler.await_pending()

        assert scheduler._registry == []
        assert executed == [1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_done_callback_removes_task_from_registry(self):
        scheduler = ServerAsyncSchedulerPort()

        async def _coro():
            return None

        task = scheduler.schedule(_coro())
        assert task in scheduler._registry
        await task
        await asyncio.sleep(0)
        assert task not in scheduler._registry

    @pytest.mark.asyncio
    async def test_no_pending_tasks_is_noop(self):
        scheduler = ServerAsyncSchedulerPort()
        await scheduler.await_pending()
        assert scheduler._registry == []
