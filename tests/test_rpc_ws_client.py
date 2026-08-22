from __future__ import annotations

from dataclasses import dataclass

import pytest

from webcompy.rpc import Procedure, batch, notify


@dataclass
class AddParams:
    a: int
    b: int = 0


def test_ws_batch_empty_no_io():
    import asyncio

    assert asyncio.run(batch()) == ()


def test_ws_notify_empty_no_io():
    import asyncio

    assert asyncio.run(notify()) is None


def test_contract_call_via_ws_requires_open():
    # RpcWsClient in non-browser is SSR no-op, call should raise
    from webcompy.di import DIScope, provide
    from webcompy.di._keys import RPC_REGISTRY_KEY
    from webcompy.rpc import RpcWsClient
    from webcompy.rpc._errors import RpcError
    from webcompy.rpc._registry import ProcedureRegistry

    registry = ProcedureRegistry()
    scope = DIScope()
    scope.__enter__()
    try:
        provide(RPC_REGISTRY_KEY, registry)
        client = RpcWsClient()
        proc = Procedure("add", AddParams, int)
        import asyncio

        async def _run():
            return await proc(client, AddParams(a=1))

        with pytest.raises(RpcError):
            asyncio.run(_run())
    finally:
        scope.__exit__(None, None, None)
