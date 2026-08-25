"""WebLoop task and microtask ordering under ``asyncio.sleep(0)``.

Contract: under the Pyodide WebLoop event loop, ``await asyncio.sleep(0)``
yields control so concurrently scheduled tasks interleave fairly, and a
``call_soon`` callback scheduled before the sleep fires before the sleeper
resumes.
"""

import asyncio


async def test_sleep_zero_yields_to_pending_tasks(app):
    order = []

    async def worker(tag):
        order.append(f"start:{tag}")
        await asyncio.sleep(0)
        order.append(f"end:{tag}")

    first = asyncio.ensure_future(worker("a"))
    second = asyncio.ensure_future(worker("b"))
    await first
    await second

    assert order == ["start:a", "start:b", "end:a", "end:b"], order


async def test_call_soon_runs_before_sleep_zero_resume(app):
    seen = []
    loop = asyncio.get_running_loop()

    def callback():
        seen.append("cb")

    async def sleeper():
        loop.call_soon(callback)
        await asyncio.sleep(0)
        seen.append("resume")

    await sleeper()

    assert seen == ["cb", "resume"], seen
