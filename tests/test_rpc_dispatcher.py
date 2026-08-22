from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest

from webcompy.rpc import Procedure
from webcompy.rpc._registry import ProcedureRegistry
from webcompy_server.rpc import create_dispatcher_app


@dataclass
class AddParams:
    a: int
    b: int = 0


@dataclass
class User:
    id: int
    name: str


@dataclass
class GetUserParams:
    user: User


def _add(p: AddParams) -> int:
    return p.a + p.b


def _get_user(p: GetUserParams) -> User:
    return p.user


def _make_app(registry: ProcedureRegistry):
    return create_dispatcher_app(registry)


def _post(app, payload: object) -> httpx.Response:
    import asyncio

    async def _request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            return await client.post("/", json=payload)

    return asyncio.run(_request())


@pytest.fixture
def registry() -> ProcedureRegistry:
    r = ProcedureRegistry()
    r.bind(Procedure("add", AddParams, int), _add)
    r.bind(Procedure("get_user", GetUserParams, User), _get_user)
    return r


def test_object_params_with_defaults(registry):
    app = _make_app(registry)
    resp = _post(app, {"jsonrpc": "2.0", "method": "add", "params": {"a": 5}, "id": 1})
    assert resp.status_code == 200
    assert resp.json()["result"] == 5


def test_array_params_rejected(registry):
    app = _make_app(registry)
    resp = _post(app, {"jsonrpc": "2.0", "method": "add", "params": [5], "id": 1})
    assert resp.json()["error"]["code"] == -32602


def test_strict_extra_key_rejected(registry):
    app = _make_app(registry)
    resp = _post(app, {"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2, "extra": 99}, "id": 1})
    assert resp.json()["error"]["code"] == -32602


def test_typed_params_reconstruction(registry):
    app = _make_app(registry)
    resp = _post(app, {"jsonrpc": "2.0", "method": "get_user", "params": {"user": {"id": 1, "name": "alice"}}, "id": 1})
    assert resp.json()["result"] == {"id": 1, "name": "alice"}


def test_batch_with_array_params_rejected(registry):
    app = _make_app(registry)
    payload = [
        {"jsonrpc": "2.0", "method": "add", "params": {"a": 1}, "id": 1},
        {"jsonrpc": "2.0", "method": "add", "params": [2], "id": 2},
    ]
    resp = _post(app, payload)
    data = resp.json()
    assert data[0]["result"] == 1
    assert data[1]["error"]["code"] == -32602
