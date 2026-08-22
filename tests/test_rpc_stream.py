from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from webcompy.rpc import StreamingProcedure
from webcompy.rpc._registry import ProcedureRegistry


@dataclass
class CountParams:
    n: int


async def _count_up(p: CountParams) -> AsyncIterator[int]:
    for i in range(1, p.n + 1):
        yield i


def test_streaming_bind_and_info():
    registry = ProcedureRegistry()
    proc = StreamingProcedure("count_up", CountParams, int)
    registry.bind(proc, _count_up)
    info = registry.get("count_up")
    assert info is not None
    assert info.is_streaming is True
    assert info.result_schema is int
