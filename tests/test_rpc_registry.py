from __future__ import annotations

import typing
from collections.abc import AsyncIterable, AsyncIterator, Iterable, Iterator
from dataclasses import dataclass
from typing import Any

import pytest

from webcompy.exception import WebComPyException
from webcompy.rpc import Procedure, StreamingProcedure, Subscription
from webcompy.rpc._registry import DEFAULT_RPC_PATH, ProcedureInfo, ProcedureRegistry


@dataclass
class AddParams:
    a: int
    b: int = 0


@dataclass
class Item:
    n: int


def _add(p: AddParams) -> int:
    return p.a + p.b


async def _concat(p: AddParams) -> int:
    return p.a + p.b


def _untyped(x) -> int:  # type: ignore[no-untyped-def]
    return x


def _kwargs_fn(**kwargs: Any) -> int:
    return len(kwargs)


def _args_fn(*args: int) -> int:
    return sum(args)


def _no_return(p: AddParams):  # type: ignore[no-untyped-def]
    return p.a


@dataclass
class StrItem:
    n: int


async def _gen_typing_async(p: AddParams) -> typing.AsyncIterator[int]:
    for i in range(1, p.a + 1):
        yield i


async def _gen_abc_async(p: AddParams) -> AsyncIterator[int]:
    for i in range(1, p.a + 1):
        yield i


async def _gen_abc_async_iterable(p: AddParams) -> AsyncIterable[Item]:
    yield Item(1)


def _gen_typing_sync(p: AddParams) -> Iterator[str]:
    yield "a"


def _gen_abc_sync(p: AddParams) -> Iterable[int]:
    yield 1


async def _gen_untyped_async(p: AddParams) -> AsyncIterator:
    yield 1


def _gen_untyped_sync(p: AddParams) -> Iterator:
    yield 1


def _plain_with_iterable_annotation(p: AddParams) -> Iterator[int]:
    return iter([1, 2])


async def _async_gen_with_sync_annotation(p: AddParams) -> Iterator[int]:
    yield 1


def _sync_gen_with_async_annotation(p: AddParams) -> AsyncIterator[int]:
    yield 1


def _gen_with_non_iterable_annotation(p: AddParams) -> int:
    yield 1  # type: ignore[misc]


class TestProcedureBind:
    def test_bind_procedure(self) -> None:
        registry = ProcedureRegistry()
        add = Procedure("add", AddParams, int)
        registry.bind(add, _add)
        info = registry.get("add")
        assert info is not None
        assert isinstance(info, ProcedureInfo)
        assert info.name == "add"
        assert info.param_schemas == {"p": AddParams}
        assert info.param_order == ["p"]
        assert info.result_schema is int
        assert info.is_async is False
        assert info.is_streaming is False

    def test_decorator_bind(self) -> None:
        registry = ProcedureRegistry()
        add = Procedure("add", AddParams, int)

        @registry.bind(add)
        def _add2(p: AddParams) -> int:
            return p.a

        assert registry.get("add") is not None

    def test_async_procedure_is_flagged(self) -> None:
        registry = ProcedureRegistry()
        add = Procedure("concat", AddParams, int)
        registry.bind(add, _concat)
        info = registry.get("concat")
        assert info is not None
        assert info.is_async is True

    def test_duplicate_name_rejected(self) -> None:
        registry = ProcedureRegistry()
        add = Procedure("sum", AddParams, int)
        registry.bind(add, _add)
        add2 = Procedure("sum", AddParams, int)
        with pytest.raises(WebComPyException, match="already registered"):
            registry.bind(add2, _add)

    def test_untyped_parameter_rejected(self) -> None:
        registry = ProcedureRegistry()
        add = Procedure("untyped", AddParams, int)
        with pytest.raises(WebComPyException, match="untyped parameter"):
            registry.bind(add, _untyped)

    def test_kwargs_rejected(self) -> None:
        registry = ProcedureRegistry()
        add = Procedure("kwargs", AddParams, int)
        with pytest.raises(WebComPyException, match=r"variadic parameter 'kwargs'"):
            registry.bind(add, _kwargs_fn)

    def test_varargs_rejected(self) -> None:
        registry = ProcedureRegistry()
        add = Procedure("args", AddParams, int)
        with pytest.raises(WebComPyException, match=r"variadic parameter 'args'"):
            registry.bind(add, _args_fn)

    def test_missing_return_annotation_rejected(self) -> None:
        registry = ProcedureRegistry()
        add = Procedure("no_return", AddParams, int)
        with pytest.raises(WebComPyException, match="missing return type annotation"):
            registry.bind(add, _no_return)

    def test_param_mismatch_rejected(self) -> None:
        registry = ProcedureRegistry()

        @dataclass
        class OtherParams:
            x: int

        add = Procedure("add", AddParams, int)

        def _wrong(p: OtherParams) -> int:
            return p.x

        with pytest.raises(WebComPyException, match="parameter type mismatch"):
            registry.bind(add, _wrong)

    def test_result_mismatch_rejected(self) -> None:
        registry = ProcedureRegistry()
        add = Procedure("add", AddParams, int)

        def _wrong(p: AddParams) -> str:
            return str(p.a)

        with pytest.raises(WebComPyException, match="return type mismatch"):
            registry.bind(add, _wrong)

    def test_generator_bound_to_procedure_rejected(self) -> None:
        registry = ProcedureRegistry()
        add = Procedure("add", AddParams, int)
        with pytest.raises(WebComPyException, match="generator functions must be bound to StreamingProcedure"):
            registry.bind(add, _gen_abc_async)  # type: ignore[arg-type]

    def test_has_procedures_and_get(self) -> None:
        registry = ProcedureRegistry()
        assert registry.has_procedures is False
        add = Procedure("add", AddParams, int)
        registry.bind(add, _add)
        assert registry.has_procedures is True
        assert registry.get("missing") is None


class TestTypeHandlers:
    def test_register_type_handler_exposes_encoders_and_decoders(self) -> None:
        registry = ProcedureRegistry()

        class Point:
            def __init__(self, x: int, y: int) -> None:
                self.x = x
                self.y = y

        def encode_point(point: Point) -> dict[str, int]:
            return {"x": point.x, "y": point.y}

        def decode_point(data: dict[str, int]) -> Point:
            return Point(data["x"], data["y"])

        registry.register_type_handler(Point, encode_point, decode_point)

        assert registry.meta_encoders == {Point: (f"{Point.__module__}.{Point.__qualname__}", encode_point)}
        assert registry.meta_decoders == {f"{Point.__module__}.{Point.__qualname__}": decode_point}
        assert registry.is_known_meta_tag(f"{Point.__module__}.{Point.__qualname__}") is True

    def test_builtin_meta_tags_are_known(self) -> None:
        registry = ProcedureRegistry()
        for tag in ("datetime", "bytes", "decimal", "uuid"):
            assert registry.is_known_meta_tag(tag) is True

    def test_unknown_tag_is_unknown(self) -> None:
        registry = ProcedureRegistry()
        assert registry.is_known_meta_tag("builtins.eval") is False


class TestPath:
    def test_default_path_and_endpoint_url(self) -> None:
        registry = ProcedureRegistry()
        assert registry.path == DEFAULT_RPC_PATH
        assert registry.endpoint_url == "/_webcompy-rpc"

    def test_endpoint_url_with_base_url(self) -> None:
        registry = ProcedureRegistry(base_url="/myapp/")
        assert registry.endpoint_url == "/myapp/_webcompy-rpc"

    def test_set_path(self) -> None:
        registry = ProcedureRegistry()
        registry.set_path("/custom/rpc")
        assert registry.path == "/custom/rpc"
        assert registry.endpoint_url == "/custom/rpc"

    def test_set_path_with_base_url(self) -> None:
        registry = ProcedureRegistry(base_url="/admin/")
        registry.set_path("/rpc")
        assert registry.endpoint_url == "/admin/rpc"

    def test_set_path_rejects_relative(self) -> None:
        registry = ProcedureRegistry()
        with pytest.raises(WebComPyException, match="absolute non-root"):
            registry.set_path("rpc")

    def test_set_path_rejects_root(self) -> None:
        registry = ProcedureRegistry()
        with pytest.raises(WebComPyException, match="absolute non-root"):
            registry.set_path("/")


class TestStreamingBind:
    def test_async_generator_typing_registers_streaming(self) -> None:
        registry = ProcedureRegistry()
        proc = StreamingProcedure("gen_typing_async", AddParams, int)
        registry.bind(proc, _gen_typing_async)
        info = registry.get("gen_typing_async")
        assert info is not None
        assert info.is_streaming is True
        assert info.result_schema is int

    def test_async_generator_abc_registers_streaming(self) -> None:
        registry = ProcedureRegistry()
        proc = StreamingProcedure("gen_abc_async", AddParams, int)
        registry.bind(proc, _gen_abc_async)
        info = registry.get("gen_abc_async")
        assert info is not None
        assert info.is_streaming is True
        assert info.result_schema is int

    def test_async_iterable_element_schema_extracted(self) -> None:
        registry = ProcedureRegistry()
        proc = StreamingProcedure("gen_abc_async_iterable", AddParams, Item)
        registry.bind(proc, _gen_abc_async_iterable)
        info = registry.get("gen_abc_async_iterable")
        assert info is not None
        assert info.is_streaming is True
        assert info.result_schema is Item

    def test_sync_generator_registers_streaming(self) -> None:
        registry = ProcedureRegistry()
        proc = StreamingProcedure("gen_typing_sync", AddParams, str)
        registry.bind(proc, _gen_typing_sync)
        info = registry.get("gen_typing_sync")
        assert info is not None
        assert info.is_streaming is True
        assert info.result_schema is str

    def test_sync_generator_abc_registers_streaming(self) -> None:
        registry = ProcedureRegistry()
        proc = StreamingProcedure("gen_abc_sync", AddParams, int)
        registry.bind(proc, _gen_abc_sync)
        info = registry.get("gen_abc_sync")
        assert info is not None
        assert info.is_streaming is True
        assert info.result_schema is int

    def test_unsubscripted_typing_annotation_rejected(self) -> None:
        registry = ProcedureRegistry()
        proc = StreamingProcedure("gen_untyped_async", AddParams, int)
        with pytest.raises(WebComPyException, match="requires an element type"):
            registry.bind(proc, _gen_untyped_async)

    def test_unsubscripted_abc_annotation_rejected(self) -> None:
        registry = ProcedureRegistry()
        proc = StreamingProcedure("gen_untyped_sync", AddParams, int)
        with pytest.raises(WebComPyException, match="requires an element type"):
            registry.bind(proc, _gen_untyped_sync)

    def test_non_generator_with_iterable_annotation_rejected(self) -> None:
        registry = ProcedureRegistry()
        proc = StreamingProcedure("plain_iterable", AddParams, int)
        with pytest.raises(WebComPyException, match="requires a generator function"):
            registry.bind(proc, _plain_with_iterable_annotation)

    def test_async_generator_with_sync_annotation_rejected(self) -> None:
        registry = ProcedureRegistry()
        proc = StreamingProcedure("async_gen_sync_annot", AddParams, int)
        with pytest.raises(WebComPyException, match="async generator function must be annotated"):
            registry.bind(proc, _async_gen_with_sync_annotation)

    def test_sync_generator_with_async_annotation_rejected(self) -> None:
        registry = ProcedureRegistry()
        proc = StreamingProcedure("sync_gen_async_annot", AddParams, int)
        with pytest.raises(WebComPyException, match="sync generator function must be annotated"):
            registry.bind(proc, _sync_gen_with_async_annotation)

    def test_generator_with_non_iterable_annotation_rejected(self) -> None:
        registry = ProcedureRegistry()
        proc = StreamingProcedure("gen_int_annot", AddParams, int)
        with pytest.raises(WebComPyException, match="iterable return annotation"):
            registry.bind(proc, _gen_with_non_iterable_annotation)

    def test_streaming_name_collides_with_procedure(self) -> None:
        registry = ProcedureRegistry()
        proc = StreamingProcedure("gen_typing_async", AddParams, int)
        registry.bind(proc, _gen_typing_async)
        add = Procedure("gen_typing_async", AddParams, int)
        with pytest.raises(WebComPyException, match="already registered"):
            registry.bind(add, _add)

    def test_streaming_shares_namespace_with_subscription(self) -> None:
        registry = ProcedureRegistry()

        @dataclass
        class TickerParams:
            ticker_id: str

        async def _ticker(p: TickerParams) -> AsyncIterator[int]:
            yield 1

        sub = Subscription("ticker", TickerParams, int)
        registry.bind(sub, _ticker)
        proc = StreamingProcedure("ticker", AddParams, int)
        with pytest.raises(WebComPyException, match="already registered"):
            registry.bind(proc, _gen_typing_async)

    def test_ordinary_procedure_is_not_streaming(self) -> None:
        registry = ProcedureRegistry()
        add = Procedure("add", AddParams, int)
        registry.bind(add, _add)
        info = registry.get("add")
        assert info is not None
        assert info.is_streaming is False
        assert info.result_schema is int


class TestSubscriptionBind:
    def test_subscription_bind(self) -> None:
        registry = ProcedureRegistry()

        @dataclass
        class TickerParams:
            ticker_id: str

        sub = Subscription("ticker", TickerParams, int)

        async def _ticker(p: TickerParams) -> AsyncIterator[int]:
            yield 1

        registry.bind(sub, _ticker)
        info = registry.get_subscription("ticker")
        assert info is not None
        assert info.replay_size == 256

    def test_replay_size_propagation(self) -> None:
        registry = ProcedureRegistry()

        @dataclass
        class TickerParams:
            ticker_id: str

        sub = Subscription("ticker", TickerParams, int, replay_size=10)

        async def _ticker(p: TickerParams) -> AsyncIterator[int]:
            yield 1

        registry.bind(sub, _ticker)
        assert registry.get_subscription("ticker").replay_size == 10  # type: ignore[union-attr]

    def test_element_mismatch_rejected(self) -> None:
        registry = ProcedureRegistry()

        @dataclass
        class TickerParams:
            ticker_id: str

        sub = Subscription("ticker", TickerParams, int)

        async def _ticker(p: TickerParams) -> AsyncIterator[str]:
            yield "x"

        with pytest.raises(WebComPyException, match="element type mismatch"):
            registry.bind(sub, _ticker)

    def test_unannotated_rejected(self) -> None:
        registry = ProcedureRegistry()

        @dataclass
        class TickerParams:
            ticker_id: str

        sub = Subscription("ticker", TickerParams, int)

        async def _ticker(p: TickerParams):  # type: ignore[no-untyped-def]
            yield 1

        with pytest.raises(WebComPyException, match="missing return type annotation"):
            registry.bind(sub, _ticker)  # type: ignore[arg-type]
