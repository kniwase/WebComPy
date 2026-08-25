"""WebLoop asyncio semantics under the Emscripten main thread.

Top-level imports must stay CPython-importable: browser-only modules are
imported inside function bodies (CPython-importability invariant).
"""

from webcompy_testing.browser_runner import skip


async def test_webloop_roundtrip():
    import asyncio

    await asyncio.sleep(0)
    flag = []
    asyncio.get_running_loop().call_soon(flag.append, 1)
    await asyncio.sleep(0)

    assert flag == [1]


async def test_scheduler_microtask(app):
    from webcompy.di import inject
    from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

    done = []

    async def work():
        await _asyncio_sleep(0)
        done.append(1)

    scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
    scheduler.schedule(work())
    await scheduler.await_pending()

    assert done == [1]


async def test_skip_helper_maps_to_skipped(app):
    skip("skip path is exercised intentionally")


async def _asyncio_sleep(delay):
    import asyncio

    await asyncio.sleep(delay)
