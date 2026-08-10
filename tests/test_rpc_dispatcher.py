from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

import httpx

from webcompy.rpc._registry import ProcedureRegistry
from webcompy_server.rpc import create_dispatcher_app


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


def _echo(value: str = "") -> str:
    return value


async def _async_echo(value: str) -> str:
    return value


def _add(a: int, b: int = 0) -> int:
    return a + b


@dataclass
class User:
    id: int
    name: str


def _get_user(user: User) -> User:
    if not isinstance(user, User):
        raise TypeError(f"expected User instance, got {type(user).__name__}")
    return user


def _get_typed() -> dict:
    return {"data": b"hello", "price": Decimal("1.5"), "at": datetime(2024, 1, 2, 3, 4, 5)}


_NOTIFICATIONS_EXECUTED: list[str] = []


def _record(name: str) -> None:
    _NOTIFICATIONS_EXECUTED.append(name)


def _boom() -> None:
    raise RuntimeError("boom")


class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


def _encode_point(point: Point) -> dict[str, int]:
    return {"x": point.x, "y": point.y}


def _decode_point(data: dict[str, int]) -> Point:
    return Point(data["x"], data["y"])


def _reflect_point(point: Point) -> Point:
    return point


def _make_registry() -> ProcedureRegistry:
    registry = ProcedureRegistry()
    registry.register("echo", _echo)
    registry.register("async_echo", _async_echo)
    registry.register("add", _add)
    registry.register("get_user", _get_user)
    registry.register("get_typed", _get_typed)
    registry.register("record", _record)
    registry.register("boom", _boom)
    return registry


class TestSingleCall:
    def test_named_params(self) -> None:
        response = _post(
            _make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2}, "id": 1}
        )
        assert response.status_code == 200
        assert response.json() == {"jsonrpc": "2.0", "result": 3, "id": 1}

    def test_positional_params(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": [1, 2], "id": "x"})
        assert response.status_code == 200
        assert response.json() == {"jsonrpc": "2.0", "result": 3, "id": "x"}

    def test_default_parameters_fill_in(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": {"a": 5}, "id": 1})
        assert response.json()["result"] == 5

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

    def test_missing_params(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "echo", "id": 1})
        assert response.json() == {"jsonrpc": "2.0", "result": "", "id": 1}

    def test_id_null_is_a_request(self) -> None:
        response = _post(
            _make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": {"a": 1}, "id": None}
        )
        assert response.status_code == 200
        assert response.json() == {"jsonrpc": "2.0", "result": 1, "id": None}

    def test_positional_params_rely_on_defaults(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": [5], "id": 1})
        assert response.status_code == 200
        assert response.json() == {"jsonrpc": "2.0", "result": 5, "id": 1}


class TestNotifications:
    def test_notification_executes_without_response_body(self) -> None:
        _NOTIFICATIONS_EXECUTED.clear()
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "record", "params": {"name": "n1"}})
        assert response.status_code == 204
        assert response.content == b""
        assert _NOTIFICATIONS_EXECUTED == ["n1"]

    def test_notification_unknown_method_no_response(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "missing"})
        assert response.status_code == 204
        assert response.content == b""

    def test_notification_invalid_params_no_response(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": {"a": "x"}})
        assert response.status_code == 204
        assert response.content == b""

    def test_notification_positional_params_rely_on_defaults(self) -> None:
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

    def test_all_notification_batch_returns_no_body(self) -> None:
        _NOTIFICATIONS_EXECUTED.clear()
        response = _post(
            _make_app(_make_registry()),
            [
                {"jsonrpc": "2.0", "method": "record", "params": {"name": "a"}},
                {"jsonrpc": "2.0", "method": "record", "params": {"name": "b"}},
            ],
        )
        assert response.status_code == 204
        assert response.content == b""
        assert _NOTIFICATIONS_EXECUTED == ["a", "b"]

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

    def test_batch_positional_params_rely_on_defaults(self) -> None:
        response = _post(
            _make_app(_make_registry()),
            [
                {"jsonrpc": "2.0", "method": "add", "params": [5], "id": 1},
                {"jsonrpc": "2.0", "method": "add", "params": [5, 2], "id": 2},
            ],
        )
        assert response.status_code == 200
        assert response.json() == [
            {"jsonrpc": "2.0", "result": 5, "id": 1},
            {"jsonrpc": "2.0", "result": 7, "id": 2},
        ]


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

    def test_invalid_params_too_many_positional(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "add", "params": [1, 2, 3], "id": 1})
        assert response.json()["error"]["code"] == -32602

    def test_internal_error_hides_details(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "boom", "id": 1})
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
            {"jsonrpc": "2.0", "method": "get_user", "params": {"user": {"id": 1, "name": "alice"}}, "id": 1},
        )
        assert response.json()["result"] == {"id": 1, "name": "alice"}

    def test_dataclass_param_extra_key_rejected(self) -> None:
        response = _post(
            _make_app(_make_registry()),
            {"jsonrpc": "2.0", "method": "get_user", "params": {"user": {"id": 1, "name": "a", "extra": 1}}, "id": 1},
        )
        assert response.json()["error"]["code"] == -32602

    def test_result_meta_for_non_json_native_values(self) -> None:
        response = _post(_make_app(_make_registry()), {"jsonrpc": "2.0", "method": "get_typed", "id": 1})
        body = response.json()
        assert body["result"] == {"data": "aGVsbG8=", "price": "1.5", "at": "2024-01-02T03:04:05"}
        assert body["meta"] == {"/data": "bytes", "/price": "decimal", "/at": "datetime"}

    def test_request_meta_closed_set_restores_value(self) -> None:
        async def _get_at(at: datetime) -> datetime:
            return at

        registry = _make_registry()
        registry.register("get_at", _get_at)
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
        assert response.json()["result"] == "2024-01-02T03:04:05"

    def test_positional_params_meta_applied_before_zip(self) -> None:
        async def _get_both(a: datetime, b: datetime) -> str:
            return f"{a}-{b}"

        registry = _make_registry()
        registry.register("get_both", _get_both)
        response = _post(
            _make_app(registry),
            {
                "jsonrpc": "2.0",
                "method": "get_both",
                "params": ["2024-01-02T03:04:05", "2024-02-02T03:04:05"],
                "meta": {"/0": "datetime", "/1": "datetime"},
                "id": 1,
            },
        )
        assert response.json()["result"] == "2024-01-02 03:04:05-2024-02-02 03:04:05"

    def test_unregistered_meta_tag_rejected(self) -> None:
        response = _post(
            _make_app(_make_registry()),
            {
                "jsonrpc": "2.0",
                "method": "echo",
                "params": {"x": 1},
                "meta": {"/x": "mystery.type"},
                "id": 1,
            },
        )
        assert response.json()["error"]["code"] == -32602

    def test_allowlisted_custom_type_round_trip(self) -> None:
        registry = _make_registry()
        registry.register_type_handler(Point, _encode_point, _decode_point)
        registry.register("reflect", _reflect_point)
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
        assert response.json()["result"] == {"x": 3, "y": 4}
        assert response.json()["meta"] == {"": tag}


class TestSecurity:
    def test_crafted_meta_never_imports_modules(self) -> None:
        for tag in ("os.system", "builtins.eval", "some.module.Class"):
            with patch("importlib.import_module") as mock_import:
                response = _post(
                    _make_app(_make_registry()),
                    {
                        "jsonrpc": "2.0",
                        "method": "echo",
                        "params": {"x": 1},
                        "meta": {"/x": tag},
                        "id": 1,
                    },
                )
                assert response.json()["error"]["code"] == -32602
                mock_import.assert_not_called()
