from __future__ import annotations

import warnings
from dataclasses import dataclass

from webcompy.di import DIScope, provide
from webcompy.di._keys import RPC_REGISTRY_KEY
from webcompy.rpc import RpcWsClient, Subscription
from webcompy.rpc._registry import ProcedureRegistry


@dataclass
class AddParams:
    a: int


@dataclass
class TickerParams:
    ticker_id: str


def test_ws_ssr_noop():
    registry = ProcedureRegistry()
    scope = DIScope()
    scope.__enter__()
    try:
        provide(RPC_REGISTRY_KEY, registry)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            client = RpcWsClient()
            assert len(w) == 1
            assert "outside the browser" in str(w[0].message)
            # subscribe in SSR should return closed subscription
            sub_proc = Subscription("ticker", TickerParams, int)
            sub = sub_proc(client, TickerParams(ticker_id="a"))
            import asyncio

            async def _collect():
                items = []
                async for _ in sub:
                    items.append(1)
                return items

            assert asyncio.run(_collect()) == []
    finally:
        scope.__exit__(None, None, None)
