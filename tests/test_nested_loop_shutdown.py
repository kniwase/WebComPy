from __future__ import annotations

# browser-dualrun: skip
import asyncio

from webcompy.aio._aio import _resolve_async_callback
from webcompy.elements.types._dynamic import _run_refresh_sync
from webcompy_testing import run_sync


async def _use_default_executor() -> None:
    await asyncio.get_running_loop().run_in_executor(None, lambda: None)


class TestCleanShutdownAfterNestedExecution:
    def test_run_sync_inside_running_loop_shuts_down_cleanly(self) -> None:
        results: list[int] = []

        async def inner() -> int:
            await asyncio.sleep(0)
            return 7

        async def main() -> None:
            results.append(run_sync(inner()))
            await _use_default_executor()

        asyncio.run(main())
        assert results == [7]

    def test_resolve_async_callback_inside_running_loop_shuts_down_cleanly(self) -> None:
        seen: list[int] = []

        async def callback(value: int) -> None:
            await asyncio.sleep(0)
            seen.append(value)

        async def main() -> None:
            _resolve_async_callback(callback, 3)
            assert seen == [3]
            await _use_default_executor()

        asyncio.run(main())
        assert seen == [3]

    def test_run_refresh_sync_inside_running_loop_shuts_down_cleanly(self) -> None:
        seen: list[str] = []

        async def refresh(tag: str) -> None:
            await asyncio.sleep(0)
            seen.append(tag)

        async def main() -> None:
            _run_refresh_sync(refresh, "a")
            assert seen == ["a"]
            _run_refresh_sync(refresh, "b")
            await _use_default_executor()

        asyncio.run(main())
        assert seen == ["a", "b"]

    def test_repeated_patching_keeps_single_patched_loop(self) -> None:
        async def inner() -> None:
            await asyncio.sleep(0)

        async def main() -> None:
            run_sync(inner())
            run_sync(inner())
            await _use_default_executor()

        asyncio.run(main())
