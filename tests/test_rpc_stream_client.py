from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from webcompy.di import DIScope, provide
from webcompy.di._keys import RPC_REGISTRY_KEY
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy.rpc import StreamingProcedure
from webcompy.rpc._contracts import RpcHttpClient


@dataclass
class CountParams:
    n: int


async def _count_up(p: CountParams) -> AsyncIterator[int]:
    for i in range(1, p.n + 1):
        yield i


def test_stream_client_ssr_returns_empty():
    from webcompy.rpc._registry import ProcedureRegistry

    registry = ProcedureRegistry()
    proc = StreamingProcedure("count_up", CountParams, int)
    registry.bind(proc, _count_up)
    scope = DIScope()
    scope.__enter__()
    try:
        provide(RPC_REGISTRY_KEY, registry)

        # no fetch port or noop -> SSR
        class FakeFetch:
            noop = True

            async def fetch(self, *a, **k):
                pass

            async def stream(self, *a, **k):
                pass

        provide(FETCH_PORT_KEY, FakeFetch())
        client = RpcHttpClient()
        import asyncio
        import warnings

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            stream = proc(client, CountParams(n=2))

            # In SSR, _stream_impl returns closed stream
            # we need to check it's a RpcStream
            # proc returns what transport.stream returns, which in SSR is RpcStream(closed=True)
            # So we can run it
            async def _check():
                # If it's a coroutine (due to missing await), handle
                if asyncio.iscoroutine(stream):
                    s = await stream
                else:
                    s = stream
                items = []
                async for x in s:
                    items.append(x)
                return items

            assert asyncio.run(_check()) == []
    finally:
        scope.__exit__(None, None, None)
