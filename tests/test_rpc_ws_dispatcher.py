from __future__ import annotations

import asyncio
from dataclasses import dataclass

from webcompy.rpc import Procedure
from webcompy.rpc._registry import ProcedureRegistry
from webcompy_server.rpc._dispatcher import dispatch_payload


@dataclass
class AddParams:
    a: int
    b: int = 0


def _add(p: AddParams) -> int:
    return p.a + p.b


def test_ws_dispatcher_single_call_object_params():
    registry = ProcedureRegistry()
    registry.bind(Procedure("add", AddParams, int), _add)
    payload = {"jsonrpc": "2.0", "method": "add", "params": {"a": 2, "b": 3}, "id": 1}
    result = asyncio.run(dispatch_payload(payload, registry))
    assert result["result"] == 5


def test_ws_dispatcher_array_params_rejected():
    registry = ProcedureRegistry()
    registry.bind(Procedure("add", AddParams, int), _add)
    payload = {"jsonrpc": "2.0", "method": "add", "params": [1, 2], "id": 1}
    result = asyncio.run(dispatch_payload(payload, registry))
    assert result["error"]["code"] == -32602
