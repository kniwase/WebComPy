from __future__ import annotations

from dataclasses import dataclass

from webcompy.rpc import Procedure, StreamingProcedure, Subscription


@dataclass
class AddParams:
    a: int
    b: int = 0


@dataclass
class TickerParams:
    ticker_id: str


@dataclass
class CountUpParams:
    n: int


@dataclass
class MockAddParams:
    """Parameters for the mock-only ``mock_add`` procedure."""

    a: int
    b: int = 0


add = Procedure("add", AddParams, int)
mock_add = Procedure("mock_add", MockAddParams, int)
ticker = Subscription("ticker", TickerParams, dict, replay_size=256)
count_up = StreamingProcedure("count_up", CountUpParams, int)
count_up_sync = StreamingProcedure("count_up_sync", CountUpParams, int)
fail_midway = StreamingProcedure("fail_midway", CountUpParams, int)
