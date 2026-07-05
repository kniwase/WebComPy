from __future__ import annotations

import asyncio
import logging

import pytest

from webcompy.aio._aio import _aio_run_server, aio_run
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
from webcompy_server.ports._async_scheduler import ServerAsyncSchedulerPort


class TestAioRunDelegationWithDIScope:
    @pytest.mark.asyncio
    async def test_aio_run_within_di_scope_uses_scheduler(self):
        scheduler = ServerAsyncSchedulerPort()
        scope = DIScope()
        scope.provide(ASYNC_SCHEDULER_PORT_KEY, scheduler)
        token = _active_di_scope.set(scope)
        try:
            executed: list[int] = []

            async def _coro() -> None:
                executed.append(99)

            _aio_run_server(_coro())
            assert scheduler._registry
            await scheduler.await_pending()
            assert executed == [99]
        finally:
            _active_di_scope.reset(token)


class TestAioRunDelegationFallback:
    @pytest.mark.asyncio
    async def test_aio_run_outside_di_scope_logs_warning_and_falls_back(self, caplog):
        scope = DIScope()
        scope.dispose()
        token = _active_di_scope.set(scope)
        try:
            executed: list[int] = []

            async def _coro() -> None:
                executed.append(7)

            with caplog.at_level(logging.WARNING, logger="uvicorn"):
                _aio_run_server(_coro())
            assert any("outside render context" in record.message for record in caplog.records)

            await asyncio.sleep(0)
            assert executed == [7]
        finally:
            _active_di_scope.reset(token)

    def test_aio_run_alias_points_to_server_function_in_non_pyscript_env(self):
        from webcompy.utils._environment import ENVIRONMENT

        if ENVIRONMENT != "pyscript":
            assert aio_run is _aio_run_server


class TestAioRunNoOrphanTasks:
    @pytest.mark.asyncio
    async def test_no_orphan_tasks_left_in_registry_after_drain(self):
        scheduler = ServerAsyncSchedulerPort()
        scope = DIScope()
        scope.provide(ASYNC_SCHEDULER_PORT_KEY, scheduler)
        token = _active_di_scope.set(scope)
        try:

            async def _noop():
                return None

            for _ in range(5):
                _aio_run_server(_noop())

            assert len(scheduler._registry) == 5
            await scheduler.await_pending()
            assert scheduler._registry == []
        finally:
            _active_di_scope.reset(token)
