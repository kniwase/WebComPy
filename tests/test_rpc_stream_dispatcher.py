from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from webcompy.rpc import StreamingProcedure
from webcompy.rpc._registry import ProcedureRegistry
from webcompy_server.rpc._dispatcher import _classify_stream_call, dispatch_payload


@dataclass
class CountParams:
    n: int


async def _count_up(p: CountParams) -> AsyncIterator[int]:
    for i in range(1, p.n + 1):
        yield i


def test_classify_stream_call():
    registry = ProcedureRegistry()
    proc = StreamingProcedure("count_up", CountParams, int)
    registry.bind(proc, _count_up)
    payload = {"jsonrpc": "2.0", "method": "count_up", "params": {"n": 2}, "id": 1, "stream": True}
    classified = _classify_stream_call(payload, registry)
    assert classified is not None
    assert classified.info.name == "count_up"


def test_streaming_not_in_batch():
    registry = ProcedureRegistry()
    proc = StreamingProcedure("count_up", CountParams, int)
    registry.bind(proc, _count_up)
    payload = [{"jsonrpc": "2.0", "method": "count_up", "params": {"n": 2}, "id": 1}]
    result = asyncio.run(dispatch_payload(payload, registry))
    # streaming in batch should be error
    assert (
        result[0]["error"]["code"] == -32600
        or result[0]["error"]["code"] == -32602
        or "streaming" in result[0]["error"]["message"]
    )
