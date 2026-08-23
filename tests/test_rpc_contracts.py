from __future__ import annotations

from dataclasses import dataclass

import pytest

from webcompy.rpc import Procedure, RpcCall, StreamingProcedure, Subscription, batch, notify
from webcompy.rpc._errors import RpcError
from webcompy.rpc._registry import ProcedureRegistry


@dataclass
class AddParams:
    a: int
    b: int = 0


@dataclass
class OtherParams:
    x: int


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.notifies = []

    async def call(self, method, params=None, *, result_type=None):
        self.calls.append((method, params, result_type))
        if result_type is int:
            return 5
        return None

    async def notify(self, method, params=None):
        self.notifies.append((method, params))

    def stream(self, method, params=None, *, result_type=None):
        from webcompy.rpc._stream import RpcStream

        return RpcStream(closed=False)

    def subscribe(self, method, params=None, *, event_type=None):
        from webcompy.rpc._ws_client import RpcSubscription

        # return closed subscription for test
        class FakeClient:
            _registry = ProcedureRegistry()

        return RpcSubscription(FakeClient(), method, params, event_type, closed=True)


def test_procedure_returns_rpc_call():
    t = FakeTransport()
    proc = Procedure("add", AddParams, int)
    c = proc(t, AddParams(2, 3))
    assert isinstance(c, RpcCall)
    import asyncio

    async def _run():
        return await c

    assert asyncio.run(_run()) == 5
    assert t.calls[0][0] == "add"


def test_rpc_call_await_once():
    t = FakeTransport()
    proc = Procedure("add", AddParams, int)
    c = proc(t, AddParams(2, 3))
    import asyncio

    async def _run2():
        await c

    asyncio.run(_run2())

    async def _run3():
        await c

    with pytest.raises(RuntimeError, match="already awaited"):
        asyncio.run(_run3())


def test_rpc_call_bool_raises():
    t = FakeTransport()
    proc = Procedure("add", AddParams, int)
    c = proc(t, AddParams(2, 3))
    with pytest.raises(TypeError):
        bool(c)
    with pytest.raises(TypeError):
        if c:
            pass
    with pytest.raises(TypeError):
        _ = c or 1
    with pytest.raises(TypeError):
        len(c)


def test_batch_empty_no_io():
    import asyncio

    # no transport needed, should return () without error
    assert asyncio.run(batch()) == ()


def test_notify_empty_no_io():
    import asyncio

    assert asyncio.run(notify()) is None


def test_streaming_procedure_returns_stream():
    t = FakeTransport()
    proc = StreamingProcedure("produce", AddParams, int)
    s = proc(t, AddParams(2, 3))
    from webcompy.rpc._stream import RpcStream

    assert isinstance(s, RpcStream)


def test_subscription_returns_subscription():
    t = FakeTransport()
    sub = Subscription("ticker", AddParams, int)
    # Use FakeTransport subscribe
    s = sub(t, AddParams(2, 3))
    # closed subscription still is RpcSubscription
    from webcompy.rpc._ws_client import RpcSubscription

    assert isinstance(s, RpcSubscription)


def test_reserved_name_rejected():
    with pytest.raises(ValueError):
        Procedure("_webcompy.internal", AddParams, int)
    with pytest.raises(ValueError):
        StreamingProcedure("_webcompy.x", AddParams, int)
    with pytest.raises(ValueError):
        Subscription("_webcompy.y", AddParams, int)


def test_non_dataclass_rejected():
    with pytest.raises(TypeError, match="dataclass"):
        Procedure("add", int, int)
    with pytest.raises(TypeError, match="dataclass"):
        Procedure("add", str, int)


def test_non_type_arg_rejected():
    with pytest.raises(TypeError):
        Procedure("add", "not a type", int)  # type: ignore
    with pytest.raises(TypeError):
        Procedure("add", AddParams, "not a type")  # type: ignore


def test_generic_alias_arg_rejected():
    with pytest.raises(TypeError):
        Procedure("add", AddParams, list[int])
    with pytest.raises(TypeError):
        StreamingProcedure("produce", AddParams, list[int])
    with pytest.raises(TypeError):
        Subscription("ticker", AddParams, dict[str, int])


def test_replay_size_validation():
    with pytest.raises(ValueError):
        Subscription("ticker", AddParams, int, replay_size=0)
    with pytest.raises(ValueError):
        Subscription("ticker", AddParams, int, replay_size=True)  # bool rejected
    with pytest.raises(ValueError):
        Subscription("ticker", AddParams, int, replay_size=-1)
    s = Subscription("ticker", AddParams, int, replay_size=10)
    assert s.replay_size == 10


def test_notify_delegation():
    import asyncio

    class Other:
        pass

    with pytest.raises(RpcError):
        asyncio.run(notify(Other()))  # type: ignore


def test_batch_rejects_non_rpc_call():
    import asyncio

    with pytest.raises(RpcError):
        asyncio.run(batch("not a call"))  # type: ignore


def test_batch_mixed_transport_rejected():
    import asyncio

    t1 = FakeTransport()
    t2 = FakeTransport()
    p1 = Procedure("add", AddParams, int)
    p2 = Procedure("add", AddParams, int)
    c1 = p1(t1, AddParams(1, 0))
    c2 = p2(t2, AddParams(2, 0))
    with pytest.raises(RpcError, match="same transport"):
        asyncio.run(batch(c1, c2))


def test_rpc_call_is_awaitable_and_batch_usable():
    from webcompy.di import DIScope, provide
    from webcompy.di._keys import RPC_REGISTRY_KEY
    from webcompy.ports._keys import FETCH_PORT_KEY

    t = FakeTransport()
    proc = Procedure("add", AddParams, int)
    c = proc(t, AddParams(2, 3))
    import asyncio

    # FakeTransport batch requires registry but will be unsupported transport
    registry = ProcedureRegistry()
    fetch_port = type("F", (), {"fetch": lambda *a, **k: None})()
    scope = DIScope()
    scope.__enter__()
    try:
        provide(RPC_REGISTRY_KEY, registry)
        provide(FETCH_PORT_KEY, fetch_port)
        with pytest.raises(RpcError, match="unsupported transport"):
            asyncio.run(batch(c))
    finally:
        scope.__exit__(None, None, None)


def _in_scope():
    from webcompy.di import DIScope, provide
    from webcompy.di._keys import RPC_REGISTRY_KEY
    from webcompy.ports._keys import FETCH_PORT_KEY

    scope = DIScope()
    scope.__enter__()
    provide(RPC_REGISTRY_KEY, ProcedureRegistry())
    provide(FETCH_PORT_KEY, type("F", (), {"fetch": lambda *a, **k: None})())
    return scope


def test_batch_marks_calls_consumed():
    import asyncio

    t = FakeTransport()
    proc = Procedure("add", AddParams, int)
    c1 = proc(t, AddParams(1, 0))
    c2 = proc(t, AddParams(2, 0))
    scope = _in_scope()
    try:
        with pytest.raises(RpcError, match="unsupported transport"):
            asyncio.run(batch(c1, c2))
        with pytest.raises(RuntimeError, match="already awaited"):

            async def _reawait_c1():
                await c1

            asyncio.run(_reawait_c1())
        with pytest.raises(RuntimeError, match="already awaited"):

            async def _reawait_c2():
                await c2

            asyncio.run(_reawait_c2())
    finally:
        scope.__exit__(None, None, None)


def test_notify_marks_calls_consumed():
    import asyncio

    t = FakeTransport()
    proc = Procedure("add", AddParams, int)
    c1 = proc(t, AddParams(1, 0))
    scope = _in_scope()
    try:
        with pytest.raises(RpcError, match="unsupported transport"):
            asyncio.run(notify(c1))
        with pytest.raises(RuntimeError, match="already awaited"):

            async def _reawait():
                await c1

            asyncio.run(_reawait())
    finally:
        scope.__exit__(None, None, None)


def test_mixed_transport_rejection_does_not_consume_calls():
    import asyncio

    t1 = FakeTransport()
    t2 = FakeTransport()
    p1 = Procedure("add", AddParams, int)
    p2 = Procedure("add", AddParams, int)
    c1 = p1(t1, AddParams(1, 0))
    c2 = p2(t2, AddParams(2, 0))
    with pytest.raises(RpcError, match="same transport"):
        asyncio.run(batch(c1, c2))

    async def _run():
        return await c1

    assert asyncio.run(_run()) == 5
