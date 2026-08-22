from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

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
class EchoParams:
    value: str = ""


@dataclass
class RecordParams:
    name: str


@dataclass
class EmptyParams:
    pass


@dataclass
class AtParams:
    at: datetime


@dataclass
class User:
    id: int
    name: str


@dataclass
class GetUserParams:
    user: User


@dataclass
class ReflectParams:
    point: Point


class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


def _encode_point(point: Point) -> dict[str, int]:
    return {"x": point.x, "y": point.y}


def _decode_point(data: dict[str, int]) -> Point:
    return Point(data["x"], data["y"])


def _add(p: AddParams) -> int:
    return p.a + p.b


def _echo(p: EchoParams) -> str:
    return p.value


async def _async_echo(p: EchoParams) -> str:
    return p.value


def _get_user(user: User) -> User:
    if not isinstance(user, User):
        raise TypeError(f"expected User instance, got {type(user).__name__}")
    return user


def _get_typed(p: EmptyParams) -> dict:
    return {"data": b"hello", "price": Decimal("1.5"), "at": datetime(2024, 1, 2, 3, 4, 5)}


def _get_at(p: AtParams) -> AtParams:
    return p


def _reflect_point(p: ReflectParams) -> ReflectParams:
    if not isinstance(p.point, Point):
        raise TypeError(f"expected Point instance, got {type(p.point).__name__}")
    return p


def _boom(p: EmptyParams) -> int:
    raise RuntimeError("boom")


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


def _post_raw(app, body: str) -> httpx.Response:
    import asyncio

    async def _request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            return await client.post("/", content=body)

    return asyncio.run(_request())


@pytest.fixture
def recorded() -> list[str]:
    return []


def _make_registry(recorded: list[str] | None = None) -> ProcedureRegistry:
    sink = recorded if recorded is not None else []

    def _record(p: RecordParams) -> None:
        sink.append(p.name)

    registry = ProcedureRegistry()
    registry.bind(Procedure("echo", EchoParams, str), _echo)
    registry.bind(Procedure("async_echo", EchoParams, str), _async_echo)
    registry.bind(Procedure("add", AddParams, int), _add)
    registry.bind(Procedure("get_user", User, User), _get_user)
    registry.bind(Procedure("get_typed", EmptyParams, dict), _get_typed)
    registry.bind(Procedure("record", RecordParams, type(None)), _record)
    registry.bind(Procedure("boom", EmptyParams, int), _boom)
    return registry


class TestSingleCall:
    def test_named_params(self) -> None:
        response = _post(
            _make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2}, "id": 1}
        )
        assert response.status_code == 200
        assert response.json() == {"jsonrpc": "2.0", "result": 3, "id": 1}

    def test_positional_params_are_rejected(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": [1, 2], "id": "x"})
        assert response.json()["error"]["code"] == -32602
        assert response.json()["id"] == "x"

    def test_default_parameters_fill_in(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": {"a": 5}, "id": 1})
        assert response.json()["result"] == 5

    def test_object_params_with_defaults(self, registry_fixture=None) -> None:
        app = _make_app(_make_registry())
        resp = _post(app, {"jsonrpc": "2.0", "method": "add", "params": {"a": 5}, "id": 1})
        assert resp.status_code == 200
        assert resp.json()["result"] == 5

    def test_array_params_rejected(self) -> None:
        app = _make_app(_make_registry())
        resp = _post(app, {"jsonrpc": "2.0", "method": "add", "params": [5], "id": 1})
        assert resp.json()["error"]["code"] == -32602

    def test_strict_extra_key_rejected(self) -> None:
        app = _make_app(_make_registry())
        resp = _post(app, {"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2, "extra": 99}, "id": 1})
        assert resp.json()["error"]["code"] == -32602

    def test_sync_procedure(self) -> None:
        response = _post(
            _make_app(_make_registry()), {"jsonrpc": "2.0", "method": "echo", "params": {"value": "hi"}, "id": 1}
        )
        assert response.json()["result"] == "hi"

    def test_async_procedure(self) -> None:
        response = _post(
            _make_app(_make_registry()), {"jsonrpc": "2.0", "method": "async_echo", "params": {"value": "hi"}, "id": 1}
        )
        assert response.json()["result"] == "hi"

    def test_missing_params_member_is_rejected(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "echo", "id": 1})
        assert response.json()["error"]["code"] == -32602

    def test_id_null_is_a_request(self) -> None:
        response = _post(
            _make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": {"a": 1}, "id": None}
        )
        assert response.status_code == 200
        assert response.json() == {"jsonrpc": "2.0", "result": 1, "id": None}


class TestNotifications:
    def test_notification_executes_without_response_body(self, recorded: list[str]) -> None:
        response = _post(
            _make_app(_make_registry(recorded)), {"jsonrpc": "2.0", "method": "record", "params": {"name": "n1"}}
        )
        assert response.status_code == 204
        assert response.content == b""
        assert recorded == ["n1"]

    def test_notification_unknown_method_no_response(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "missing"})
        assert response.status_code == 204
        assert response.content == b""

    def test_notification_invalid_params_no_response(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": {"a": "x"}})
        assert response.status_code == 204
        assert response.content == b""

    def test_notification_positional_params_no_response(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": [5]})
        assert response.status_code == 204
        assert response.content == b""


class TestBatch:
    def test_mixed_batch_returns_only_call_responses(self) -> None:
        response = _post(
            _make_app(_make_registry()),
            [
                {"jsonrpc": "2.0", "method": "add", "params": {"a": 1}, "id": 1},
                {"jsonrpc": "2.0", "method": "record", "params": {"name": "n"}},
                {"jsonrpc": "2.0", "method": "add", "params": {"a": 2}, "id": 2},
            ],
        )
        assert response.status_code == 200
        assert response.json() == [
            {"jsonrpc": "2.0", "result": 1, "id": 1},
            {"jsonrpc": "2.0", "result": 2, "id": 2},
        ]

    def test_all_notification_batch_returns_no_body(self, recorded: list[str]) -> None:
        response = _post(
            _make_app(_make_registry(recorded)),
            [
                {"jsonrpc": "2.0", "method": "record", "params": {"name": "a"}},
                {"jsonrpc": "2.0", "method": "record", "params": {"name": "b"}},
            ],
        )
        assert response.status_code == 204
        assert response.content == b""
        assert recorded == ["a", "b"]

    def test_empty_batch_array_returns_invalid_request(self) -> None:
        response = _post(_make_app(_make_registry()), [])
        assert response.status_code == 200
        assert response.json()["error"]["code"] == -32600
        assert response.json()["id"] is None

    def test_batch_entries_processed_independently(self) -> None:
        response = _post(
            _make_app(_make_registry()),
            [
                {"jsonrpc": "2.0", "method": "missing", "id": 1},
                {"jsonrpc": "2.0", "method": "add", "params": {"a": 1}, "id": 2},
            ],
        )
        data = response.json()
        by_id = {entry["id"]: entry for entry in data}
        assert by_id[1]["error"]["code"] == -32601
        assert by_id[2]["result"] == 1

    def test_batch_positional_params_rejected_per_entry(self) -> None:
        response = _post(
            _make_app(_make_registry()),
            [
                {"jsonrpc": "2.0", "method": "add", "params": [5], "id": 1},
                {"jsonrpc": "2.0", "method": "add", "params": [5, 2], "id": 2},
            ],
        )
        data = response.json()
        by_id = {entry["id"]: entry for entry in data}
        assert by_id[1]["error"]["code"] == -32602
        assert by_id[2]["error"]["code"] == -32602

    def test_batch_with_array_params_rejected(self) -> None:
        payload = [
            {"jsonrpc": "2.0", "method": "add", "params": {"a": 1}, "id": 1},
            {"jsonrpc": "2.0", "method": "add", "params": [2], "id": 2},
        ]
        resp = _post(_make_app(_make_registry()), payload)
        data = resp.json()
        by_id = {entry["id"]: entry for entry in data}
        assert by_id[1]["result"] == 1
        assert by_id[2]["error"]["code"] == -32602


class TestErrorCodes:
    def test_parse_error(self) -> None:
        response = _post_raw(_make_app(_make_registry()), "{invalid json")
        assert response.status_code == 200
        body = response.json()
        assert body["error"]["code"] == -32700
        assert body["id"] is None

    def test_invalid_request_non_object(self) -> None:
        for payload in ("foo", 42, True):
            response = _post(_make_app(_make_registry()), payload)
            assert response.json()["error"]["code"] == -32600

    def test_invalid_request_missing_jsonrpc(self) -> None:
        response = _post(_make_app(_make_registry()), {"method": "add", "params": {"a": 1}, "id": 1})
        assert response.json()["error"]["code"] == -32600

    def test_invalid_request_wrong_jsonrpc_version(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "1.0", "method": "add", "params": {"a": 1}, "id": 1})
        assert response.json()["error"]["code"] == -32600

    def test_invalid_request_missing_method(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "params": {}, "id": 1})
        assert response.json()["error"]["code"] == -32600

    def test_invalid_request_non_string_method(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": 42, "id": 1})
        assert response.json()["error"]["code"] == -32600

    def test_invalid_request_bool_id(self) -> None:
        response = _post(
            _make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": {"a": 1}, "id": True}
        )
        assert response.json()["error"]["code"] == -32600
        assert response.json()["id"] is None

    def test_method_not_found(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "missing", "id": 1})
        assert response.json()["error"]["code"] == -32601
        assert response.json()["id"] == 1

    def test_invalid_params_non_container(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": "nope", "id": 1})
        assert response.json()["error"]["code"] == -32602

    def test_invalid_params_wrong_type(self) -> None:
        response = _post(
            _make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": {"a": "x"}, "id": 1}
        )
        assert response.json()["error"]["code"] == -32602

    def test_invalid_params_missing_required(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": {"b": 2}, "id": 1})
        assert response.json()["error"]["code"] == -32602

    def test_invalid_params_unknown_name(self) -> None:
        response = _post(
            _make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "c": 3}, "id": 1}
        )
        assert response.json()["error"]["code"] == -32602

    def test_internal_error_hides_details(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "boom", "params": {}, "id": 1})
        body = response.json()
        assert body["error"]["code"] == -32603
        assert body["error"]["message"] == "Internal error"
        assert "boom" not in body["error"]["message"]

    def test_method_not_allowed(self) -> None:
        import asyncio

        async def _request() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=_make_app(_make_registry())),
                base_url="http://test",
            ) as client:
                return await client.get("/")

        response = asyncio.run(_request())
        assert response.status_code == 405


class TestTypedDecoding:
    def test_dataclass_param_reconstructed(self) -> None:
        response = _post(
            _make_app(_make_registry()),
            {"jsonrpc": "2.0", "method": "get_user", "params": {"id": 1, "name": "alice"}, "id": 1},
        )
        assert response.json()["result"] == {"id": 1, "name": "alice"}

    def test_dataclass_param_extra_key_rejected(self) -> None:
        response = _post(
            _make_app(_make_registry()),
            {"jsonrpc": "2.0", "method": "get_user", "params": {"id": 1, "name": "a", "extra": 1}, "id": 1},
        )
        assert response.json()["error"]["code"] == -32602

    def test_result_meta_for_non_json_native_values(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "get_typed", "params": {}, "id": 1})
        body = response.json()
        assert body["result"] == {"data": "aGVsbG8=", "price": "1.5", "at": "2024-01-02T03:04:05"}
        assert body["meta"] == {"/data": "bytes", "/price": "decimal", "/at": "datetime"}

    def test_request_meta_closed_set_restores_value(self) -> None:
        registry = _make_registry()
        registry.bind(Procedure("get_at", AtParams, AtParams), _get_at)
        response = _post(
            _make_app(registry),
            {
                "jsonrpc": "2.0",
                "method": "get_at",
                "params": {"at": "2024-01-02T03:04:05"},
                "meta": {"/at": "datetime"},
                "id": 1,
            },
        )
        body = response.json()
        assert body["result"] == {"at": "2024-01-02T03:04:05"}
        assert body["meta"] == {"/at": "datetime"}

    def test_unregistered_meta_tag_rejected(self) -> None:
        response = _post(
            _make_app(_make_registry()),
            {
                "jsonrpc": "2.0",
                "method": "echo",
                "params": {"value": "x"},
                "meta": {"/value": "mystery.type"},
                "id": 1,
            },
        )
        assert response.json()["error"]["code"] == -32602

    def test_allowlisted_custom_type_round_trip(self) -> None:
        registry = _make_registry()
        registry.register_type_handler(Point, _encode_point, _decode_point)
        registry.bind(Procedure("reflect", ReflectParams, ReflectParams), _reflect_point)
        tag = f"{Point.__module__}.{Point.__qualname__}"
        response = _post(
            _make_app(registry),
            {
                "jsonrpc": "2.0",
                "method": "reflect",
                "params": {"point": {"x": 3, "y": 4}},
                "meta": {"/point": tag},
                "id": 1,
            },
        )
        body = response.json()
        assert body["result"] == {"point": {"x": 3, "y": 4}}
        assert body["meta"] == {"/point": tag}


class TestSecurity:
    def test_crafted_meta_never_imports_modules(self) -> None:
        for tag in ("os.system", "builtins.eval", "some.module.Class"):
            with patch("importlib.import_module") as mock_import:
                response = _post(
                    _make_app(_make_registry()),
                    {
                        "jsonrpc": "2.0",
                        "method": "echo",
                        "params": {"value": "x"},
                        "meta": {"/value": tag},
                        "id": 1,
                    },
                )
                assert response.json()["error"]["code"] == -32602
                mock_import.assert_not_called()


def _get_nested_user_impl(p: GetUserParams) -> User:
    return p.user


def test_nested_dataclass_param_reconstruction():
    registry = ProcedureRegistry()
    registry.bind(Procedure("get_user", GetUserParams, User), _get_nested_user_impl)
    app = _make_app(registry)
    resp = _post(app, {"jsonrpc": "2.0", "method": "get_user", "params": {"user": {"id": 1, "name": "alice"}}, "id": 1})
    assert resp.json()["result"] == {"id": 1, "name": "alice"}
