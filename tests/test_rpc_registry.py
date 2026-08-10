from __future__ import annotations

from typing import Any

import pytest

from webcompy.exception import WebComPyException
from webcompy.rpc._registry import DEFAULT_RPC_PATH, ProcedureInfo, ProcedureRegistry


def _add(a: int, b: int = 0) -> int:
    return a + b


async def _concat(items: list[str]) -> str:
    return "".join(items)


def _untyped(x) -> int:  # type: ignore[no-untyped-def]
    return x


def _kwargs_fn(**kwargs: Any) -> int:
    return len(kwargs)


def _args_fn(*args: int) -> int:
    return sum(args)


def _no_return(x: int):  # type: ignore[no-untyped-def]
    return x


class TestProcedureRegistration:
    def test_decorator_registration(self) -> None:
        registry = ProcedureRegistry()

        registry.procedure(_add)

        info = registry.get("_add")
        assert info is not None
        assert isinstance(info, ProcedureInfo)
        assert info.name == "_add"
        assert info.param_schemas == {"a": int, "b": int}
        assert info.param_order == ["a", "b"]
        assert info.required == frozenset({"a"})
        assert info.result_schema is int
        assert info.is_async is False

    def test_async_procedure_is_flagged(self) -> None:
        registry = ProcedureRegistry()

        registry.procedure(_concat)

        info = registry.get("_concat")
        assert info is not None
        assert info.is_async is True

    def test_explicit_registration_with_custom_name(self) -> None:
        registry = ProcedureRegistry()

        registry.register("sum", _add)

        assert registry.get("sum") is not None
        assert registry.get("_add") is None

    def test_duplicate_name_rejected(self) -> None:
        registry = ProcedureRegistry()
        registry.register("sum", _add)

        with pytest.raises(WebComPyException, match="already registered"):
            registry.register("sum", _add)

    def test_untyped_parameter_rejected_with_name(self) -> None:
        registry = ProcedureRegistry()

        with pytest.raises(WebComPyException, match="untyped parameter"):
            registry.register("untyped", _untyped)

    def test_kwargs_rejected(self) -> None:
        registry = ProcedureRegistry()

        with pytest.raises(WebComPyException, match=r"variadic parameter 'kwargs'"):
            registry.register("kwargs", _kwargs_fn)

    def test_varargs_rejected(self) -> None:
        registry = ProcedureRegistry()

        with pytest.raises(WebComPyException, match=r"variadic parameter 'args'"):
            registry.register("args", _args_fn)

    def test_missing_return_annotation_rejected(self) -> None:
        registry = ProcedureRegistry()

        with pytest.raises(WebComPyException, match="missing return type annotation"):
            registry.register("no_return", _no_return)

    def test_has_procedures_and_get(self) -> None:
        registry = ProcedureRegistry()
        assert registry.has_procedures is False
        registry.procedure(_add)
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
