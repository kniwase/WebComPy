from __future__ import annotations

import dataclasses
import enum
import json
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from webcompy.hydration import (
    decode,
    encode,
    has_resolved_data,
    register_type_handler,
)
from webcompy.hydration._codec import (
    _type_handlers,
    _type_handlers_by_name,
)
from webcompy.hydration._payload import (
    TransferAsyncResultEntry,
    TransferFetchEntry,
    TransferPayload,
    deserialize_payload,
    serialize_payload,
)


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"
    GREEN = "green"


class Priority(enum.IntEnum):
    LOW = 1
    HIGH = 10


class Status(enum.StrEnum):
    OK = "ok"
    FAIL = "fail"


@dataclasses.dataclass
class CodecTestAddress:
    city: str
    zip: str


@dataclasses.dataclass
class CodecTestUser:
    name: str
    age: int
    address: CodecTestAddress


@dataclasses.dataclass
class PayloadUserProfile:
    name: str
    age: int


@pytest.fixture(autouse=True)
def _reset_plugin_registry():
    yield
    _type_handlers.clear()
    _type_handlers_by_name.clear()


class TestEncodePassthrough:
    def test_int_passthrough(self):
        assert encode(42) == 42

    def test_string_passthrough(self):
        assert encode("hello") == "hello"

    def test_none_passthrough(self):
        assert encode(None) is None

    def test_bool_passthrough(self):
        assert encode(True) is True
        assert encode(False) is False

    def test_float_passthrough(self):
        assert encode(3.14) == 3.14

    def test_list_passthrough(self):
        assert encode([1, 2, 3]) == [1, 2, 3]

    def test_dict_passthrough(self):
        assert encode({"a": 1, "b": "c"}) == {"a": 1, "b": "c"}

    def test_nested_dict_passthrough(self):
        nested = {"key": "value", "count": 42, "list": [1, 2, "x"]}
        assert encode(nested) == nested


class TestDecodePassthrough:
    def test_int_passthrough(self):
        assert decode(42) == 42

    def test_string_passthrough(self):
        assert decode("hello") == "hello"

    def test_none_passthrough(self):
        assert decode(None) is None

    def test_list_passthrough(self):
        assert decode([1, 2, 3]) == [1, 2, 3]

    def test_dict_passthrough(self):
        assert decode({"a": 1, "b": "c"}) == {"a": 1, "b": "c"}

    def test_user_dict_without_reserved_key_is_not_a_type_tag(self):
        result = decode({"name": "Alice", "age": 30})
        assert result == {"name": "Alice", "age": 30}


class TestDatetime:
    def test_datetime_round_trip(self):
        dt = datetime(2026, 7, 4, 12, 0, 0)
        encoded = encode(dt)
        assert encoded == {
            "__webcompy_type__": "datetime",
            "__webcompy_value__": "2026-07-04T12:00:00",
        }
        decoded = decode(encoded)
        assert decoded == dt
        assert isinstance(decoded, datetime)

    def test_datetime_with_timezone_round_trip(self):
        dt = datetime(2026, 7, 4, 12, 0, tzinfo=UTC)
        encoded = encode(dt)
        decoded = decode(encoded)
        assert decoded == dt
        assert decoded.tzinfo is not None

    def test_date_round_trip(self):
        d = date(2026, 7, 4)
        encoded = encode(d)
        assert encoded["__webcompy_type__"] == "date"
        assert encoded["__webcompy_value__"] == "2026-07-04"
        decoded = decode(encoded)
        assert decoded == d
        assert isinstance(decoded, date)

    def test_time_round_trip(self):
        t = time(14, 30, 45)
        encoded = encode(t)
        assert encoded["__webcompy_type__"] == "time"
        decoded = decode(encoded)
        assert decoded == t
        assert isinstance(decoded, time)


class TestCollections:
    def test_set_round_trip(self):
        original = {1, 2, 3}
        encoded = encode(original)
        assert encoded["__webcompy_type__"] == "set"
        assert isinstance(encoded["__webcompy_value__"], list)
        decoded = decode(encoded)
        assert decoded == original
        assert isinstance(decoded, set)

    def test_empty_set_round_trip(self):
        original = set()
        decoded = decode(encode(original))
        assert decoded == original

    def test_frozenset_round_trip(self):
        original = frozenset([1, 2, 3])
        encoded = encode(original)
        assert encoded["__webcompy_type__"] == "frozenset"
        decoded = decode(encoded)
        assert decoded == original
        assert isinstance(decoded, frozenset)

    def test_tuple_round_trip_preserves_tuple_type(self):
        original = (1, 2, 3)
        encoded = encode(original)
        assert encoded["__webcompy_type__"] == "tuple"
        decoded = decode(encoded)
        assert decoded == original
        assert isinstance(decoded, tuple)
        assert not isinstance(decoded, list)


class TestEnum:
    def test_enum_round_trip(self):
        encoded = encode(Color.RED)
        assert encoded["__webcompy_type__"] == "enum"
        assert encoded["__webcompy_value__"]["module"] == __name__
        assert encoded["__webcompy_value__"]["name"] == "Color"
        assert encoded["__webcompy_value__"]["value"] == "red"
        decoded = decode(encoded)
        assert decoded == Color.RED
        assert isinstance(decoded, Color)

    def test_enum_by_value_lookup(self):
        encoded = encode(Color.GREEN)
        decoded = decode(encoded)
        assert decoded is Color.GREEN


class TestBytes:
    def test_bytes_round_trip(self):
        original = b"hello"
        encoded = encode(original)
        assert encoded["__webcompy_type__"] == "bytes"
        assert encoded["__webcompy_value__"] == "aGVsbG8="
        decoded = decode(encoded)
        assert decoded == original
        assert isinstance(decoded, bytes)


class TestDecimal:
    def test_decimal_round_trip(self):
        original = Decimal("3.14159")
        encoded = encode(original)
        assert encoded["__webcompy_type__"] == "decimal"
        assert encoded["__webcompy_value__"] == "3.14159"
        decoded = decode(encoded)
        assert decoded == original
        assert isinstance(decoded, Decimal)

    def test_decimal_precision_preserved(self):
        original = Decimal("0.123456789012345678901234567890")
        decoded = decode(encode(original))
        assert decoded == original


class TestDataclass:
    def test_dataclass_round_trip(self):
        original = CodecTestUser(name="Alice", age=30, address=CodecTestAddress(city="NYC", zip="10001"))
        encoded = encode(original)
        assert encoded["__webcompy_type__"] == "dataclass"
        decoded = decode(encoded)
        assert decoded == original
        assert isinstance(decoded, CodecTestUser)

    def test_nested_dataclass_preserves_inner_type(self):
        original = CodecTestUser(name="Bob", age=42, address=CodecTestAddress(city="LA", zip="90001"))
        encoded = encode(original)
        assert isinstance(encoded["__webcompy_value__"]["fields"]["address"], dict)
        assert encoded["__webcompy_value__"]["fields"]["address"]["__webcompy_type__"] == "dataclass"
        decoded = decode(encoded)
        assert isinstance(decoded.address, CodecTestAddress)
        assert not isinstance(decoded.address, dict)
        assert decoded.address.city == "LA"


class TestPath:
    def test_path_round_trip(self):
        original = Path("/tmp/foo/bar")
        encoded = encode(original)
        assert encoded["__webcompy_type__"] == "path"
        decoded = decode(encoded)
        assert decoded == original
        assert isinstance(decoded, Path)


class TestUUID:
    def test_uuid_round_trip(self):
        original = UUID("12345678-1234-5678-1234-567812345678")
        encoded = encode(original)
        assert encoded["__webcompy_type__"] == "uuid"
        decoded = decode(encoded)
        assert decoded == original
        assert isinstance(decoded, UUID)


class TestNestedStructures:
    def test_dict_containing_set_containing_datetime(self):
        original = {"when": {datetime(2026, 7, 4, 12, 0), datetime(2026, 7, 5, 13, 0)}}
        decoded = decode(encode(original))
        assert decoded == original
        for v in decoded["when"]:
            assert isinstance(v, datetime)

    def test_list_of_mixed_types(self):
        original = [
            datetime(2026, 7, 4),
            {1, 2, 3},
            Decimal("1.5"),
            frozenset([4, 5, 6]),
            Path("/x"),
            UUID("12345678-1234-5678-1234-567812345678"),
        ]
        decoded = decode(encode(original))
        assert decoded == original

    def test_deeply_nested_structure(self):
        original = {
            "level1": {
                "level2": [
                    {"level3": {datetime(2026, 7, 4)}},
                    {"level3": {frozenset([1, 2])}},
                ]
            }
        }
        decoded = decode(encode(original))
        assert decoded == original


class TestCircularReferences:
    def test_self_referential_dict(self, caplog):
        d: dict = {"a": 1}
        d["self"] = d
        with caplog.at_level("WARNING"):
            encoded = encode(d)
        assert encoded == {"a": 1, "self": None}
        assert any("Circular reference" in msg for msg in caplog.messages)

    def test_transitively_circular(self, caplog):
        a: dict = {"name": "a"}
        b: dict = {"name": "b", "ref": a}
        a["ref"] = b
        encoded = encode(a)
        assert encoded["ref"]["ref"] is None

    def test_list_with_self_reference(self):
        lst: list = [1, 2]
        lst.append(lst)
        encoded = encode(lst)
        assert encoded == [1, 2, None]

    def test_self_referential_dataclass(self, caplog):
        @dataclasses.dataclass
        class Node:
            next: object = None

        n = Node()
        n.next = n
        with caplog.at_level("WARNING"):
            encoded = encode(n)
        assert encoded["__webcompy_value__"]["fields"]["next"] is None
        assert any("Circular reference" in msg for msg in caplog.messages)

    def test_circular_reference_through_tuple_element(self, caplog):
        d: dict = {"key": "val"}
        inner = (d,)
        d["ref"] = inner
        with caplog.at_level("WARNING"):
            encoded = encode(d)
        assert encoded["key"] == "val"
        assert encoded["ref"]["__webcompy_type__"] == "tuple"
        assert encoded["ref"]["__webcompy_value__"] == [None]
        assert any("Circular reference" in msg for msg in caplog.messages)


class TestPluginAPI:
    def test_register_and_use_custom_handler(self):
        class MyType:
            def __init__(self, x):
                self.x = x

            def __eq__(self, other):
                return isinstance(other, MyType) and self.x == other.x

        def my_encoder(obj):
            return {"x": obj.x}

        def my_decoder(payload):
            return MyType(payload["x"])

        register_type_handler(MyType, my_encoder, my_decoder)

        original = MyType(42)
        encoded = encode(original)
        assert "__webcompy_type__" in encoded
        assert "MyType" in encoded["__webcompy_type__"]
        decoded = decode(encoded)
        assert decoded == original
        assert isinstance(decoded, MyType)

    def test_custom_handler_takes_precedence_over_builtin(self):
        from datetime import datetime

        original = datetime(2026, 7, 4, 12, 0)
        sentinel = "custom_datetime_marker"

        def custom_encoder(obj):
            return {"marker": sentinel}

        def custom_decoder(payload):
            return payload.get("marker")

        register_type_handler(datetime, custom_encoder, custom_decoder)

        encoded = encode(original)
        assert encoded["__webcompy_value__"] == {"marker": sentinel}
        decoded = decode(encoded)
        assert decoded == sentinel


class TestReservedKeyViolation:
    def test_reserved_key_emits_warning(self, caplog):
        with caplog.at_level("WARNING"):
            encode({"__webcompy_type__": "custom", "data": 123})
        assert any("Reserved key" in msg for msg in caplog.messages)


class TestBackwardCompat:
    def test_v1_payload_without_type_tags_decodes_correctly(self):
        v1_structure = {
            "async_results": {"cmp-1": {"state": "success", "data": {"name": "Alice"}}},
            "fetches": {},
        }
        assert decode(v1_structure) == v1_structure

    def test_encode_passthrough_for_plain_values(self):
        assert encode({"key": "value", "count": 42}) == {"key": "value", "count": 42}


class TestPayloadIntegration:
    def test_async_result_with_datetime_round_trip(self):
        payload = TransferPayload(
            async_results={
                "cmp-1": TransferAsyncResultEntry(
                    state="success",
                    data={"created": datetime(2026, 7, 4), "name": "Alice"},
                ),
            },
        )
        serialized = serialize_payload(payload)
        result = deserialize_payload(serialized)
        assert result is not None
        assert "cmp-1" in result.async_results
        data = result.async_results["cmp-1"].data
        assert isinstance(data["created"], datetime)
        assert data["created"] == datetime(2026, 7, 4)

    def test_async_result_with_dataclass_round_trip(self):
        payload = TransferPayload(
            async_results={
                "cmp-1": TransferAsyncResultEntry(
                    state="success",
                    data=PayloadUserProfile(name="Alice", age=30),
                ),
            },
        )
        serialized = serialize_payload(payload)
        result = deserialize_payload(serialized)
        assert result is not None
        data = result.async_results["cmp-1"].data
        assert isinstance(data, PayloadUserProfile)
        assert data.name == "Alice"
        assert data.age == 30

    def test_payload_version_is_current(self):
        payload = TransferPayload(
            async_results={
                "cmp-1": TransferAsyncResultEntry(state="success", data={"x": 1}),
            },
        )
        serialized = serialize_payload(payload)
        result = deserialize_payload(serialized)
        assert result is not None
        assert result.__webcompy_transfer_version__ == 3

    def test_non_serializable_value_dropped_with_warning(self, caplog):
        class NonSerializable:
            pass

        payload = TransferPayload(
            async_results={
                "cmp-1": TransferAsyncResultEntry(
                    state="success",
                    data={"obj": NonSerializable()},
                ),
            },
        )
        with caplog.at_level("WARNING"):
            serialized = serialize_payload(payload)
        result = deserialize_payload(serialized)
        assert result is not None
        assert "cmp-1" not in result.async_results
        assert any("Cannot encode" in msg or "Excluding" in msg for msg in caplog.messages)

    def test_existing_async_result_plain_json_still_works(self):
        payload = TransferPayload(
            fetches={
                "/api/x": TransferFetchEntry(status_code=200, headers={"a": "b"}, body="hello"),
            },
            async_results={
                "cmp-1": TransferAsyncResultEntry(state="success", data={"name": "Alice", "count": 42}),
            },
        )
        serialized = serialize_payload(payload)
        result = deserialize_payload(serialized)
        assert result is not None
        assert result.async_results["cmp-1"].data == {"name": "Alice", "count": 42}
        assert result.fetches["/api/x"].body == "hello"

    def test_serialized_payload_is_valid_json_after_unescape(self):
        import html

        payload = TransferPayload(
            fetches={"/test": TransferFetchEntry(status_code=200, headers={}, body="ok")},
        )
        serialized = serialize_payload(payload)
        parsed = json.loads(html.unescape(serialized))
        assert parsed["__webcompy_transfer_version__"] == 3


class TestPublicApiExports:
    def test_public_api_includes_encode(self):
        assert encode is not None

    def test_public_api_includes_decode(self):
        assert decode is not None

    def test_public_api_includes_register_type_handler(self):
        assert register_type_handler is not None

    def test_has_resolved_data_still_exported(self):
        assert has_resolved_data is not None


class TestDecodeFailurePaths:
    def test_unknown_type_tag_returns_none(self):
        result = decode({"__webcompy_type__": "nonexistent", "__webcompy_value__": "x"})
        assert result is None

    def test_invalid_qualified_payload_returns_none(self):
        result = decode({"__webcompy_type__": "dataclass", "__webcompy_value__": "not a dict"})
        assert result is None

    def test_missing_module_or_name(self):
        result = decode(
            {
                "__webcompy_type__": "dataclass",
                "__webcompy_value__": {"module": "definitely_nonexistent_module_xyz"},
            }
        )
        assert result is None

    def test_invalid_enum_value_returns_none(self):
        encoded = encode(Color.RED)
        encoded["__webcompy_value__"]["value"] = "purple"
        assert decode(encoded) is None

    def test_custom_handler_decoder_exception_swallowed(self, caplog):
        class Flaky:
            pass

        def good_encoder(obj):
            return {"x": 1}

        def bad_decoder(payload):
            raise RuntimeError("decoder boom")

        register_type_handler(Flaky, good_encoder, bad_decoder)

        type_name = _type_handlers[Flaky][0]
        encoded = {"__webcompy_type__": type_name, "__webcompy_value__": {"x": 1}}
        with caplog.at_level("ERROR"):
            result = decode(encoded)
        assert result is None
        assert any("Failed to decode" in msg for msg in caplog.messages)


class TestLayer2EncoderExceptionSafety:
    def test_encoder_exception_does_not_propagate(self, caplog):
        class BadCustom:
            pass

        def bad_encoder(obj):
            raise RuntimeError("encoder boom")

        register_type_handler(BadCustom, bad_encoder, lambda p: None)

        with caplog.at_level("ERROR"):
            result = encode(BadCustom())

        assert result is None
        assert any("Custom encoder for BadCustom failed" in msg for msg in caplog.messages)

    def test_encoder_exception_marks_failure_flag(self):
        from webcompy.hydration._codec import _FailureFlag

        class BadCustom:
            pass

        def bad_encoder(obj):
            raise RuntimeError("encoder boom")

        register_type_handler(BadCustom, bad_encoder, lambda p: None)

        flag = _FailureFlag()
        result = encode(BadCustom(), _flag=flag)

        assert result is None
        assert flag.failed is True


class TestIntEnumStrEnum:
    def test_int_enum_preserves_type(self):
        encoded = encode(Priority.HIGH)
        assert encoded["__webcompy_type__"] == "enum"
        assert encoded["__webcompy_value__"]["value"] == 10
        decoded = decode(encoded)
        assert isinstance(decoded, Priority)
        assert decoded is Priority.HIGH

    def test_str_enum_preserves_type(self):
        encoded = encode(Status.OK)
        assert encoded["__webcompy_type__"] == "enum"
        assert encoded["__webcompy_value__"]["value"] == "ok"
        decoded = decode(encoded)
        assert isinstance(decoded, Status)
        assert decoded is Status.OK


class TestNoDoubleEncodeWarning:
    def test_payload_serialize_does_not_warn_on_reserved_keys(self, caplog):
        payload = TransferPayload(
            async_results={
                "cmp-1": TransferAsyncResultEntry(
                    state="success",
                    data={"when": datetime(2026, 7, 4), "name": "Alice"},
                ),
            },
        )
        with caplog.at_level("WARNING"):
            serialized = serialize_payload(payload)
        assert "Reserved key" not in caplog.text
        result = deserialize_payload(serialized)
        assert result is not None
        assert result.async_results["cmp-1"].data["when"] == datetime(2026, 7, 4)

    def test_collect_then_serialize_does_not_warn_on_reserved_keys(self, caplog):
        async_results = {
            "cmp-1": TransferAsyncResultEntry(
                state="success",
                data={"when": datetime(2026, 7, 4)},
            ),
        }

        with caplog.at_level("WARNING"):
            serialize_payload(
                TransferPayload(
                    __webcompy_transfer_version__=1,
                    async_results=async_results,
                )
            )
        assert "Reserved key" not in caplog.text


class TestEntryGranularBestEffort:
    def test_single_unencodable_subvalue_drops_whole_entry(self, caplog):
        class Unencodable:
            pass

        payload = TransferPayload(
            async_results={
                "cmp-good": TransferAsyncResultEntry(
                    state="success",
                    data={"x": 1},
                ),
                "cmp-bad": TransferAsyncResultEntry(
                    state="success",
                    data={"bad": Unencodable()},
                ),
            },
        )
        with caplog.at_level("WARNING"):
            serialized = serialize_payload(payload)
        result = deserialize_payload(serialized)
        assert result is not None
        assert "cmp-good" in result.async_results
        assert "cmp-bad" not in result.async_results
        assert any("Cannot encode" in m or "Excluding" in m for m in caplog.messages)

    def test_nested_failure_in_dataclass_field_drops_entry(self, caplog):
        @dataclasses.dataclass
        class Box:
            item: object = None

        class Unencodable:
            pass

        payload = TransferPayload(
            async_results={
                "cmp-1": TransferAsyncResultEntry(state="success", data=Box(item=Unencodable())),
            },
        )
        with caplog.at_level("WARNING"):
            serialized = serialize_payload(payload)
        result = deserialize_payload(serialized)
        assert result is not None
        assert "cmp-1" not in result.async_results
        assert any("Cannot encode" in m or "Excluding" in m for m in caplog.messages)

    def test_unencodable_element_in_set_drops_entry(self, caplog):
        class HashableUnencodable:
            def __hash__(self):
                return 1

            def __eq__(self, other):
                return isinstance(other, HashableUnencodable)

        payload = TransferPayload(
            async_results={
                "cmp-1": TransferAsyncResultEntry(
                    state="success",
                    data={HashableUnencodable()},
                ),
            },
        )
        with caplog.at_level("WARNING"):
            serialized = serialize_payload(payload)
        result = deserialize_payload(serialized)
        assert result is not None
        assert "cmp-1" not in result.async_results
        assert any("Cannot encode" in m or "Excluding" in m for m in caplog.messages)
