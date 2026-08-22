from __future__ import annotations

from dataclasses import dataclass
from typing import assert_type

from webcompy.rpc import Procedure, StreamingProcedure, Subscription, batch, notify
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


def test_batch_tuple_inference() -> None:
    client = RpcHttpClient()
    c1 = add(client, AddParams(a=1))
    c2 = get_user(client, GetUserParams(id=1))
    reveal = batch(c1, c2)  # pyright should infer tuple[int, User]
    assert_type(reveal, object)
    empty = batch()
    assert_type(empty, object)


def test_notify_returns_none() -> None:
    client = RpcHttpClient()
    c = add(client, AddParams(a=1))
    reveal = notify(c)
    assert_type(reveal, object)
    empty = notify()
    assert_type(empty, object)


def test_rpc_stream_element_type() -> None:
    client = RpcHttpClient()
    s = stream_proc(client, GetUserParams(id=1))
    assert_type(s, RpcStream[Item])


def test_rpc_subscription_element_type() -> None:
    assert_type(sub_proc, Subscription[GetUserParams, Item])


def test_rpc_call_generic() -> None:
    client = RpcHttpClient()
    c = add(client, AddParams(a=1))
    assert_type(c, RpcCall[AddParams, int])
