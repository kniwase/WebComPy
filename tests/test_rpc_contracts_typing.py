from __future__ import annotations

from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any, assert_type

from webcompy.rpc import Procedure, RpcError, StreamingProcedure, Subscription, batch, notify
from webcompy.rpc._contracts import RpcCall, RpcHttpClient
from webcompy.rpc._stream import RpcStream


@dataclass
class AddParams:
    a: int
    b: int = 0


@dataclass
class GetUserParams:
    id: int


@dataclass
class User:
    id: int
    name: str


@dataclass
class Item:
    n: int


add = Procedure("add", AddParams, int)
get_user = Procedure("get_user", GetUserParams, User)
stream_proc = StreamingProcedure("produce", GetUserParams, Item)
sub_proc = Subscription("ticker", GetUserParams, Item)


def test_batch_heterogeneous_tuple_inference() -> None:
    client = RpcHttpClient()
    c1 = add(client, AddParams(a=1))
    c2 = get_user(client, GetUserParams(id=1))
    reveal = batch(c1, c2)
    assert_type(reveal, Coroutine[Any, Any, tuple[int, User]])


def test_batch_empty_inference() -> None:
    empty = batch()
    assert_type(empty, Coroutine[Any, Any, tuple[()]])


def test_batch_return_exceptions_inference() -> None:
    client = RpcHttpClient()
    c1 = add(client, AddParams(a=1))
    c2 = get_user(client, GetUserParams(id=1))
    reveal = batch(c1, c2, return_exceptions=True)
    assert_type(reveal, Coroutine[Any, Any, tuple[int | RpcError, User | RpcError]])


def test_batch_variadic_fallback_inference() -> None:
    client = RpcHttpClient()
    calls = [add(client, AddParams(a=n)) for n in range(3)]
    variadic = batch(*calls)
    assert_type(variadic, Coroutine[Any, Any, tuple[Any, ...]])


def test_notify_returns_none() -> None:
    client = RpcHttpClient()
    c = add(client, AddParams(a=1))
    reveal = notify(c)
    assert_type(reveal, Coroutine[Any, Any, None])
    empty = notify()
    assert_type(empty, Coroutine[Any, Any, None])


def test_rpc_stream_element_type() -> None:
    import warnings

    from webcompy.di import DIScope, provide
    from webcompy.di._keys import RPC_REGISTRY_KEY
    from webcompy.ports._keys import FETCH_PORT_KEY
    from webcompy.rpc._registry import ProcedureRegistry

    class _NoopPort:
        noop = True

        async def fetch(self, *args, **kwargs): ...

        async def stream(self, *args, **kwargs): ...

    scope = DIScope()
    scope.__enter__()
    try:
        provide(RPC_REGISTRY_KEY, ProcedureRegistry())
        provide(FETCH_PORT_KEY, _NoopPort())
        client = RpcHttpClient()
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            s = stream_proc(client, GetUserParams(id=1))
        assert_type(s, RpcStream[Item])
        assert isinstance(s, RpcStream)
    finally:
        scope.__exit__(None, None, None)


def test_rpc_subscription_element_type() -> None:
    assert_type(sub_proc, Subscription[GetUserParams, Item])


def test_rpc_call_generic() -> None:
    client = RpcHttpClient()
    c = add(client, AddParams(a=1))
    assert_type(c, RpcCall[AddParams, int])
