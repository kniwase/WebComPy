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
        await scheduler.drain()

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

    @pytest.mark.asyncio
    async def test_render_only_await_pending_skips_plain_tasks(self):
        scheduler = FakeAsyncSchedulerPort()
        executed: list[str] = []

        async def _render_coro():
            executed.append("r")

        async def _plain_coro():
            executed.append("p")

        scheduler.schedule(_plain_coro())
        scheduler.schedule(_render_coro(), render=True)
        await scheduler.await_pending(only_render=True)
        assert executed == ["r"]
        assert scheduler._coroutines  # plain task still pending
        await scheduler.await_pending()
        assert sorted(executed) == ["p", "r"]
        assert scheduler._coroutines == []

    @pytest.mark.asyncio
    async def test_drain_executes_recursively_scheduled_coroutines(self):
        scheduler = FakeAsyncSchedulerPort()
        done: list[int] = []

        async def _nested(value: int):
            done.append(value)
            if value < 3:
                scheduler.schedule(_nested(value + 1))

        scheduler.schedule(_nested(1))
        await scheduler.drain()
        assert sorted(done) == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_render_only_await_pending_drains_recursive_render_tasks(self):
        scheduler = FakeAsyncSchedulerPort()
        done: list[int] = []

        async def _nested(value: int):
            done.append(value)
            if value < 3:
                scheduler.schedule(_nested(value + 1), render=True)

        scheduler.schedule(_nested(1), render=True)
        await scheduler.await_pending(only_render=True)
        assert sorted(done) == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_drain_settles_placeholders_and_fires_callbacks(self):
        scheduler = FakeAsyncSchedulerPort()
        fired: list[object] = []

        async def _coro():
            pass

        task = scheduler.schedule(_coro())
        task.add_done_callback(fired.append)
        assert not task.done()
        await scheduler.drain()
        assert task.done()
        assert task.cancelled() is False
        assert task.exception() is None
        assert fired == [task]

    @pytest.mark.asyncio
    async def test_drain_records_exception_on_placeholder(self):
        scheduler = FakeAsyncSchedulerPort()

        async def _boom():
            raise RuntimeError("boom")

        task = scheduler.schedule(_boom())
        await scheduler.drain()
        assert task.done()
        assert task.cancelled() is False
        assert isinstance(task.exception(), RuntimeError)

    @pytest.mark.asyncio
    async def test_cancel_of_executed_placeholder_returns_false(self):
        scheduler = FakeAsyncSchedulerPort()

        async def _coro():
            pass

        task = scheduler.schedule(_coro())
        await scheduler.drain()
        assert task.cancel() is False
        assert task.cancelled() is False

    @pytest.mark.asyncio
    async def test_render_only_drain_does_not_settle_plain_placeholder(self):
        scheduler = FakeAsyncSchedulerPort()

        async def _render_coro():
            pass

        async def _plain_coro():
            pass

        render_task = scheduler.schedule(_render_coro(), render=True)
        plain_task = scheduler.schedule(_plain_coro())
        await scheduler.await_pending(only_render=True)
        assert render_task.done()
        assert not plain_task.done()
        await scheduler.drain()
        assert plain_task.done()


class TestBrowserAsyncSchedulerPort:
    @staticmethod
    def _make():
        # Construct without the pyscript environment gate (the ENVIRONMENT
        # check is a process-import-time binding, so monkeypatching the module
        # attribute does not affect it once imported elsewhere).
        from webcompy.ports._browser._async_scheduler import BrowserAsyncSchedulerPort

        port = object.__new__(BrowserAsyncSchedulerPort)
        port._registry = []
        return port

    @pytest.mark.asyncio
    async def test_await_pending_drains_scheduled_tasks(self):
        scheduler = self._make()
        executed: list[int] = []

        async def _task(value: int):
            await asyncio.sleep(0)
            executed.append(value)

        scheduler.schedule(_task(1))
        scheduler.schedule(_task(2))
        await scheduler.await_pending()
        assert sorted(executed) == [1, 2]

    @pytest.mark.asyncio
    async def test_await_pending_drains_recursive_scheduling(self):
        scheduler = self._make()
        done: list[int] = []

        async def _nested(value: int):
            done.append(value)
            if value < 3:
                scheduler.schedule(_nested(value + 1))

        scheduler.schedule(_nested(1))
        await scheduler.await_pending()
        assert sorted(done) == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_scheduled_exception_does_not_propagate(self):
        scheduler = self._make()

        async def _boom():
            raise RuntimeError("boom")

        scheduler.schedule(_boom())
        await scheduler.await_pending()
        assert not scheduler._registry

    @pytest.mark.asyncio
    async def test_await_pending_render_only_ignores_other_tasks(self):
        scheduler = self._make()
        gate = asyncio.Event()
        render_done: list[str] = []
        plain_done: list[str] = []

        async def _render_task():
            render_done.append("render")

        async def _blocking():
            await gate.wait()
            plain_done.append("plain")

        scheduler.schedule(_blocking())
        scheduler.schedule(_render_task(), render=True)
        await scheduler.await_pending(only_render=True)
        assert render_done == ["render"]
        assert plain_done == []  # non-render task did not block the drain
        gate.set()
        await asyncio.sleep(0)
        assert plain_done == ["plain"]

    @pytest.mark.asyncio
    async def test_await_pending_render_only_drains_recursive_render_tasks(self):
        scheduler = self._make()
        done: list[int] = []

        async def _nested(value: int):
            done.append(value)
            if value < 3:
                scheduler.schedule(_nested(value + 1), render=True)

        scheduler.schedule(_nested(1), render=True)
        await scheduler.await_pending(only_render=True)
        assert sorted(done) == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_await_pending_render_only_keeps_plain_tasks_registered(self):
        scheduler = self._make()
        gate = asyncio.Event()
        executed: list[str] = []

        async def _render_task():
            executed.append("render")

        async def _blocking():
            await gate.wait()
            executed.append("plain")

        scheduler.schedule(_blocking())
        scheduler.schedule(_render_task(), render=True)
        await scheduler.await_pending(only_render=True)
        assert executed == ["render"]
        assert not gate.is_set()
        registered_plain = any(not render for _, render in scheduler._registry)
        assert registered_plain, "render-only drain must not unregister non-render tasks"
        gate.set()
        await scheduler.await_pending()
        assert "plain" in executed
