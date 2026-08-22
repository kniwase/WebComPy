from __future__ import annotations

from dataclasses import dataclass

from webcompy.di import DIScope, provide
from webcompy.di._keys import RPC_REGISTRY_KEY
from webcompy.ports._fetch import Response
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy.rpc import Procedure
from webcompy.rpc._contracts import RpcHttpClient
from webcompy.rpc._registry import ProcedureRegistry


@dataclass
class AddParams:
    a: int
    b: int = 0


def _add(p: AddParams) -> int:
    return p.a + p.b


def test_integration_contract_call_via_fetch():
    registry = ProcedureRegistry()
    add = Procedure("add", AddParams, int)
    registry.bind(add, _add)

    # fake fetch that echoes
    class FakeFetch:
        async def fetch(self, url, method="POST", headers=None, body=None):
            import json

            payload = json.loads(body)

            from webcompy_server.rpc._dispatcher import dispatch_payload

            result = await dispatch_payload(payload, registry)
            return Response(text=json.dumps(result), headers={}, status_code=200, status_text="OK", ok=True)

    scope = DIScope()
    scope.__enter__()
    try:
        provide(RPC_REGISTRY_KEY, registry)
        provide(FETCH_PORT_KEY, FakeFetch())
        client = RpcHttpClient()
        import asyncio

        async def _run():
            return await add(client, AddParams(a=1, b=2))

        result = asyncio.run(_run())
        assert result == 3
    finally:
        scope.__exit__(None, None, None)
