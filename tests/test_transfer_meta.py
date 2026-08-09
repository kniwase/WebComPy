from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import BaseModel

from webcompy.exception import WebComPyException
from webcompy.hydration._transfer_meta import (
    META_BODY_KEY,
    apply_transfer_meta,
    encode_with_meta,
    merge_meta_into_body,
)


class Color(Enum):
    RED = "red"
    BLUE = "blue"


@dataclass
class Avatar:
    data: bytes
    label: str


@dataclass
class Profile:
    name: str
    avatar: Avatar
    tags: set[str]
    history: tuple[int, str]
    price: Decimal
    created_at: datetime
    day: date
    when: time
    uid: UUID
    path: Path
    color: Color
    extra: dict[str, str] = field(default_factory=dict)


class ProfileModel(BaseModel):
    name: str
    tags: set[str]
    price: Decimal
    avatar: bytes


class TestEncodePlain:
    def test_pure_json_passthrough(self):
        data = {"a": 1, "b": ["x", True, None], "c": {"d": 1.5}}
        json_data, meta = encode_with_meta(data)
        assert json_data == data
        assert meta == {}

    def test_list_top_level(self):
        json_data, meta = encode_with_meta([1, "a", {"b": 2}])
        assert json_data == [1, "a", {"b": 2}]
        assert meta == {}

    def test_scalar_top_level(self):
        json_data, meta = encode_with_meta(42)
        assert json_data == 42
        assert meta == {}


class TestEncodeTags:
    def test_bytes(self):
        json_data, meta = encode_with_meta({"avatar": b"hello"})
        assert json_data == {"avatar": base64.b64encode(b"hello").decode("ascii")}
        assert meta == {"/avatar": "bytes"}

    def test_set(self):
        json_data, meta = encode_with_meta({"tags": {"a", "b"}})
        assert set(json_data["tags"]) == {"a", "b"}
        assert meta == {"/tags": "set"}

    def test_frozenset(self):
        json_data, meta = encode_with_meta({"tags": frozenset({"a", "b"})})
        assert set(json_data["tags"]) == {"a", "b"}
        assert meta == {"/tags": "frozenset"}

    def test_tuple(self):
        json_data, meta = encode_with_meta({"point": (1, "x")})
        assert json_data == {"point": [1, "x"]}
        assert meta == {"/point": "tuple"}

    def test_decimal(self):
        json_data, meta = encode_with_meta({"price": Decimal("12.34")})
        assert json_data == {"price": "12.34"}
        assert meta == {"/price": "decimal"}

    def test_datetime(self):
        dt = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
        json_data, meta = encode_with_meta({"created_at": dt})
        assert json_data == {"created_at": dt.isoformat()}
        assert meta == {"/created_at": "datetime"}

    def test_date(self):
        json_data, meta = encode_with_meta({"day": date(2026, 1, 2)})
        assert json_data == {"day": "2026-01-02"}
        assert meta == {"/day": "date"}

    def test_time(self):
        json_data, meta = encode_with_meta({"when": time(3, 4, 5)})
        assert json_data == {"when": "03:04:05"}
        assert meta == {"/when": "time"}

    def test_uuid(self):
        uid = UUID("12345678-1234-5678-1234-567812345678")
        json_data, meta = encode_with_meta({"uid": uid})
        assert json_data == {"uid": str(uid)}
        assert meta == {"/uid": "uuid"}

    def test_path(self):
        json_data, meta = encode_with_meta({"path": Path("/tmp/x")})
        assert json_data == {"path": "/tmp/x"}
        assert meta == {"/path": "path"}

    def test_nested_list_paths(self):
        json_data, meta = encode_with_meta({"items": [{"blob": b"x"}, {"blob": b"y"}]})
        assert json_data["items"][0]["blob"] == base64.b64encode(b"x").decode("ascii")
        assert meta == {"/items/0/blob": "bytes", "/items/1/blob": "bytes"}

    def test_top_level_tagged_value(self):
        json_data, meta = encode_with_meta(b"root")
        assert json_data == base64.b64encode(b"root").decode("ascii")
        assert meta == {"": "bytes"}

    def test_top_level_list_items(self):
        json_data, meta = encode_with_meta([b"a", b"b"])
        assert json_data == [
            base64.b64encode(b"a").decode("ascii"),
            base64.b64encode(b"b").decode("ascii"),
        ]
        assert meta == {"/0": "bytes", "/1": "bytes"}


class TestEncodeDataclass:
    def test_dataclass_fields_inline(self):
        profile = Profile(
            name="alice",
            avatar=Avatar(data=b"img", label="pic"),
            tags={"a"},
            history=(1, "x"),
            price=Decimal("1.5"),
            created_at=datetime(2026, 1, 1),
            day=date(2026, 1, 1),
            when=time(1, 2),
            uid=UUID("12345678-1234-5678-1234-567812345678"),
            path=Path("/p"),
            color=Color.RED,
        )
        json_data, meta = encode_with_meta(profile)
        assert json_data["name"] == "alice"
        assert json_data["avatar"] == {"data": base64.b64encode(b"img").decode("ascii"), "label": "pic"}
        assert json_data["color"] == "red"
        assert json_data["extra"] == {}
        assert meta == {
            "/avatar/data": "bytes",
            "/tags": "set",
            "/history": "tuple",
            "/price": "decimal",
            "/created_at": "datetime",
            "/day": "date",
            "/when": "time",
            "/uid": "uuid",
            "/path": "path",
        }

    def test_enum_emits_value_without_tag(self):
        json_data, meta = encode_with_meta({"color": Color.BLUE})
        assert json_data == {"color": "blue"}
        assert meta == {}

    def test_no_webcompy_keys_in_body(self):
        json_data, meta = encode_with_meta({"blob": b"x", "nested": {"tags": {1, 2}}})
        dumped = repr(json_data)
        assert "__webcompy_" not in dumped
        assert meta


class TestEncodePydantic:
    def test_model_via_model_dump(self):
        model = ProfileModel(name="bob", tags={"x", "y"}, price=Decimal("9.99"), avatar=b"pic")
        json_data, meta = encode_with_meta(model)
        assert set(json_data["tags"]) == {"x", "y"}
        assert json_data["price"] == "9.99"
        assert json_data["avatar"] == base64.b64encode(b"pic").decode("ascii")
        assert meta == {"/tags": "set", "/price": "decimal", "/avatar": "bytes"}


class TestEncodeErrors:
    def test_unknown_type_raises(self):
        class Custom:
            pass

        with pytest.raises(WebComPyException, match="Cannot encode"):
            encode_with_meta({"x": Custom()})

    def test_circular_reference_raises(self):
        data: dict[str, object] = {"name": "x"}
        data["self"] = data
        with pytest.raises(WebComPyException, match="Circular reference"):
            encode_with_meta(data)

    def test_shared_reference_is_not_circular(self):
        shared = {"blob": b"x"}
        json_data, meta = encode_with_meta({"a": shared, "b": shared})
        assert json_data["a"] == json_data["b"]
        assert meta == {"/a/blob": "bytes", "/b/blob": "bytes"}


class TestEncodePaths:
    def test_keys_with_special_characters(self):
        data = {"a/b": b"x", "ti~lde": b"y", "dot.key": b"z", "bra[ck]et": b"w"}
        json_data, meta = encode_with_meta(data)
        assert meta == {
            "/a~1b": "bytes",
            "/ti~0lde": "bytes",
            "/dot.key": "bytes",
            "/bra[ck]et": "bytes",
        }
        restored = apply_transfer_meta(json_data, meta)
        assert restored["a/b"] == b"x"
        assert restored["ti~lde"] == b"y"
        assert restored["dot.key"] == b"z"
        assert restored["bra[ck]et"] == b"w"


class TestMergeMetaIntoBody:
    def test_object_payload(self):
        body = merge_meta_into_body({"name": "alice"}, {"/blob": "bytes"})
        assert body["name"] == "alice"
        assert body[META_BODY_KEY] == {"/blob": "bytes"}

    def test_array_payload_raises(self):
        with pytest.raises(WebComPyException, match="top-level JSON object"):
            merge_meta_into_body([1, 2], {"/0": "bytes"})

    def test_scalar_payload_raises(self):
        with pytest.raises(WebComPyException, match="top-level JSON object"):
            merge_meta_into_body(42, {})


class TestApplyTransferMeta:
    def test_restores_bytes(self):
        data = {"avatar": base64.b64encode(b"hi").decode("ascii")}
        assert apply_transfer_meta(data, {"/avatar": "bytes"}) == {"avatar": b"hi"}

    def test_restores_set(self):
        assert apply_transfer_meta({"tags": ["a", "b"]}, {"/tags": "set"}) == {"tags": {"a", "b"}}

    def test_restores_frozenset(self):
        assert apply_transfer_meta({"tags": ["a"]}, {"/tags": "frozenset"}) == {"tags": frozenset({"a"})}

    def test_restores_tuple(self):
        assert apply_transfer_meta({"point": [1, "x"]}, {"/point": "tuple"}) == {"point": (1, "x")}

    def test_restores_decimal(self):
        assert apply_transfer_meta({"price": "12.34"}, {"/price": "decimal"}) == {"price": Decimal("12.34")}

    def test_restores_datetime(self):
        dt = datetime(2026, 1, 2, 3, 4, 5)
        assert apply_transfer_meta({"at": dt.isoformat()}, {"/at": "datetime"}) == {"at": dt}

    def test_restores_date(self):
        assert apply_transfer_meta({"day": "2026-01-02"}, {"/day": "date"}) == {"day": date(2026, 1, 2)}

    def test_restores_time(self):
        assert apply_transfer_meta({"when": "03:04:05"}, {"/when": "time"}) == {"when": time(3, 4, 5)}

    def test_restores_uuid(self):
        uid = UUID("12345678-1234-5678-1234-567812345678")
        assert apply_transfer_meta({"uid": str(uid)}, {"/uid": "uuid"}) == {"uid": uid}

    def test_restores_path(self):
        assert apply_transfer_meta({"path": "/tmp/x"}, {"/path": "path"}) == {"path": Path("/tmp/x")}

    def test_restores_root(self):
        data = base64.b64encode(b"root").decode("ascii")
        assert apply_transfer_meta(data, {"": "bytes"}) == b"root"

    def test_deepest_path_applied_first(self):
        data = {
            "point": [
                {"blob": base64.b64encode(b"x").decode("ascii"), "label": "a"},
            ]
        }
        meta = {"/point": "tuple", "/point/0/blob": "bytes"}
        restored = apply_transfer_meta(data, meta)
        assert restored == {"point": ({"blob": b"x", "label": "a"},)}

    def test_input_not_mutated(self):
        data = {"tags": ["a"], "blob": base64.b64encode(b"x").decode("ascii")}
        original = {"tags": ["a"], "blob": base64.b64encode(b"x").decode("ascii")}
        apply_transfer_meta(data, {"/tags": "set", "/blob": "bytes"})
        assert data == original

    def test_none_meta_returns_input(self):
        data = {"a": 1}
        assert apply_transfer_meta(data, None) == data

    def test_empty_meta_returns_input(self):
        data = {"a": 1}
        assert apply_transfer_meta(data, {}) == data

    def test_unknown_tag_lenient_leaves_value(self):
        data = {"x": 1}
        assert apply_transfer_meta(data, {"/x": "future-type"}) == data

    def test_unknown_tag_strict_raises(self):
        with pytest.raises(ValueError, match="Unknown transfer meta tag"):
            apply_transfer_meta({"x": 1}, {"/x": "future-type"}, strict=True)

    def test_missing_path_raises(self):
        with pytest.raises(ValueError, match="does not exist"):
            apply_transfer_meta({"a": 1}, {"/b": "bytes"})

    def test_invalid_pointer_raises(self):
        with pytest.raises(ValueError, match="JSON Pointer"):
            apply_transfer_meta({"a": 1}, {"a": "bytes"})

    def test_malformed_tagged_value_raises(self):
        with pytest.raises(ValueError, match="Failed to decode"):
            apply_transfer_meta({"x": "not-base64!!"}, {"/x": "bytes"})

    def test_malformed_decimal_raises(self):
        with pytest.raises(ValueError, match="Failed to decode"):
            apply_transfer_meta({"price": "abc"}, {"/price": "decimal"})

    def test_non_mapping_meta_raises(self):
        with pytest.raises(ValueError, match="must be a mapping"):
            apply_transfer_meta({"a": 1}, ["/a"])

    def test_set_tag_with_non_array_raises(self):
        with pytest.raises(ValueError, match="Failed to decode"):
            apply_transfer_meta({"x": {"a": 1}}, {"/x": "set"})
