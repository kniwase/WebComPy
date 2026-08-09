from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from webcompy.ajax._serde import from_json


@dataclass
class TypedRecord:
    name: str
    blob: bytes
    tags: set[str]
    frozen: frozenset[int]
    point: tuple[int, str]
    price: Decimal
    at: datetime
    day: date
    when: time
    uid: UUID
    anything: Any


def _meta_record_body() -> dict[str, object]:
    return {
        "name": "alice",
        "blob": base64.b64encode(b"img").decode("ascii"),
        "tags": ["a", "b"],
        "frozen": [1, 2],
        "point": [1, "x"],
        "price": "12.34",
        "at": "2026-01-02T03:04:05",
        "day": "2026-01-02",
        "when": "03:04:05",
        "uid": "12345678-1234-5678-1234-567812345678",
        "anything": base64.b64encode(b"hi").decode("ascii"),
    }


def _meta_record_meta() -> dict[str, str]:
    return {
        "/blob": "bytes",
        "/tags": "set",
        "/frozen": "frozenset",
        "/point": "tuple",
        "/price": "decimal",
        "/at": "datetime",
        "/day": "date",
        "/when": "time",
        "/uid": "uuid",
        "/anything": "bytes",
    }


class TestFromJsonWithMeta:
    def test_restores_all_tags(self):
        record = from_json(TypedRecord, _meta_record_body(), meta=_meta_record_meta())
        assert record.blob == b"img"
        assert record.tags == {"a", "b"}
        assert record.frozen == frozenset({1, 2})
        assert record.point == (1, "x")
        assert record.price == Decimal("12.34")
        assert record.at == datetime(2026, 1, 2, 3, 4, 5)
        assert record.day == date(2026, 1, 2)
        assert record.when == time(3, 4, 5)
        assert record.uid == UUID("12345678-1234-5678-1234-567812345678")
        assert record.anything == b"hi"
        assert record.name == "alice"

    def test_metadata_takes_precedence_for_recorded_paths(self):
        record = from_json(TypedRecord, _meta_record_body(), meta=_meta_record_meta())
        assert isinstance(record.blob, bytes)
        assert isinstance(record.tags, set)
        assert isinstance(record.point, tuple)

    def test_absent_meta_is_purely_schema_driven(self):
        with pytest.raises(TypeError, match="blob"):
            from_json(TypedRecord, _meta_record_body())

    def test_unknown_tag_lenient_leaves_value(self):
        body = _meta_record_body()
        body["anything"] = 42
        meta = _meta_record_meta()
        meta["/anything"] = "future-type"
        record = from_json(TypedRecord, body, meta=meta)
        assert record.anything == 42

    def test_unknown_tag_strict_raises(self):
        with pytest.raises(ValueError, match="Unknown transfer meta tag"):
            from_json(TypedRecord, {"anything": 42}, meta={"/anything": "future-type"}, strict=True)

    def test_input_data_not_mutated(self):
        body = _meta_record_body()
        original = dict(body)
        from_json(TypedRecord, body, meta=_meta_record_meta())
        assert body == original


class TestSetTupleCoercion:
    def test_set_field_with_native_set_passes(self):
        assert from_json(set[str], {"a", "b"}) == {"a", "b"}

    def test_set_field_with_list_raises(self):
        with pytest.raises(TypeError, match="expected set"):
            from_json(set[str], ["a", "b"])

    def test_set_member_coercion(self):
        assert from_json(set[int], {1, 2}) == {1, 2}

    def test_set_member_mismatch_raises(self):
        with pytest.raises(TypeError):
            from_json(set[int], {"a"})

    def test_frozenset_field(self):
        assert from_json(frozenset[int], frozenset({1})) == frozenset({1})

    def test_tuple_fixed_length(self):
        assert from_json(tuple[int, str], (1, "x")) == (1, "x")

    def test_tuple_wrong_length_raises(self):
        with pytest.raises(TypeError, match="expected 2-tuple"):
            from_json(tuple[int, str], (1, "x", 3))

    def test_tuple_variadic(self):
        assert from_json(tuple[int, ...], (1, 2, 3)) == (1, 2, 3)

    def test_bare_set_and_tuple(self):
        assert from_json(set, {"a"}) == {"a"}
        assert from_json(tuple, (1, "x")) == (1, "x")

    def test_list_input_for_tuple_raises(self):
        with pytest.raises(TypeError, match="expected tuple"):
            from_json(tuple[int, str], [1, "x"])

    def test_tuple_member_coercion(self):
        assert from_json(tuple[float, float], (1, 2)) == (1.0, 2.0)
