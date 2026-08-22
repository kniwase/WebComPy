from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from webcompy.di import DIScope, provide
from webcompy.di._keys import RPC_REGISTRY_KEY
from webcompy.rpc import RpcWsClient, StreamingProcedure
from webcompy.rpc._registry import ProcedureRegistry


@dataclass
class CountParams:
    n: int


async def _count_up(p: CountParams) -> AsyncIterator[int]:
    for i in range(1, p.n + 1):
        yield i


def test_ws_stream_requires_open():
    registry = ProcedureRegistry()
    proc = StreamingProcedure("count_up", CountParams, int)
    registry.bind(proc, _count_up)
    scope = DIScope()
    scope.__enter__()
    try:
        provide(RPC_REGISTRY_KEY, registry)
        client = RpcWsClient()
        # In SSR, stream returns closed
        s = proc(client, CountParams(n=2))
        import asyncio

        async def _check():
            if asyncio.iscoroutine(s):
                stream = await s
            else:
                stream = s
            from webcompy.rpc._stream import RpcStream

            assert isinstance(stream, RpcStream)
            items = [x async for x in stream]
            return items

        assert asyncio.run(_check()) == []
    finally:
        scope.__exit__(None, None, None)
