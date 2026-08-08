from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from datetime import date, datetime, time
from enum import Enum
from typing import Optional, Union
from uuid import UUID

import pytest

from webcompy.ajax._serde import TypedResponseError, from_json


class Role(Enum):
    ADMIN = "admin"
    USER = "user"


@dataclass
class User:
    id: int
    name: str


@dataclass
class Team:
    name: str
    members: list[User]
    leader: Optional[User] = None  # noqa: UP045
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class Record:
    created_at: datetime
    day: date
    when: time
    uid: UUID
    role: Role


@dataclass
class WithUnion:
    value: Union[int, str]  # noqa: UP007


@dataclass
class WithUnionPipe:
    value: int | str


@dataclass
class WithDefaults:
    name: str
    count: int = 0


@dataclass
class WithInitVar:
    id: int
    name: str
    archived: InitVar[bool] = False


class TestFlat:
    def test_flat_dataclass(self):
        assert from_json(User, {"id": 1, "name": "ada"}) == User(id=1, name="ada")

    def test_unknown_key_ignored_by_default(self):
        assert from_json(User, {"id": 1, "name": "ada", "new_field": 42}) == User(id=1, name="ada")

    def test_unknown_key_rejected_in_strict(self):
        with pytest.raises(TypeError, match="new_field"):
            from_json(User, {"id": 1, "name": "ada", "new_field": 42}, strict=True)

    def test_missing_required_field_raises(self):
        with pytest.raises(TypeError, match="missing required field"):
            from_json(User, {"id": 1})

    def test_missing_optional_field_uses_default(self):
        assert from_json(WithDefaults, {"name": "x"}) == WithDefaults(name="x", count=0)

    def test_type_mismatch_names_field(self):
        with pytest.raises(TypeError, match="expected str"):
            from_json(User, {"id": 1, "name": 42})

    def test_init_var_field_ignored_when_absent(self):
        assert from_json(WithInitVar, {"id": 1, "name": "ada"}) == WithInitVar(id=1, name="ada")

    def test_init_var_field_ignored_when_present(self):
        assert from_json(WithInitVar, {"id": 1, "name": "ada", "archived": True}) == WithInitVar(id=1, name="ada")
        assert from_json(WithInitVar, {"id": 1, "name": "ada", "archived": True}, strict=True) == WithInitVar(
            id=1, name="ada"
        )


class TestNested:
    def test_nested_dataclass(self):
        data = {"name": "core", "members": [{"id": 1, "name": "ada"}]}
        result = from_json(Team, data)
        assert isinstance(result, Team)
        assert isinstance(result.members[0], User)
        assert result.members[0].name == "ada"

    def test_optional_none(self):
        assert from_json(Team, {"name": "core", "members": [], "leader": None}).leader is None

    def test_optional_present(self):
        result = from_json(Team, {"name": "core", "members": [], "leader": {"id": 1, "name": "ada"}})
        assert isinstance(result.leader, User)

    def test_dict_field(self):
        result = from_json(Team, {"name": "core", "members": [], "tags": {"a": "b"}})
        assert result.tags == {"a": "b"}

    def test_nested_strict_propagates(self):
        data = {"name": "core", "members": [{"id": 1, "name": "ada", "extra": 1}]}
        with pytest.raises(TypeError, match="extra"):
            from_json(Team, data, strict=True)


class TestUnion:
    def test_union_matches_declaration_order(self):
        assert from_json(WithUnion, {"value": "x"}) == WithUnion(value="x")
        assert from_json(WithUnion, {"value": 5}) == WithUnion(value=5)

    def test_union_pipe_syntax(self):
        assert from_json(WithUnionPipe, {"value": "x"}) == WithUnionPipe(value="x")

    def test_union_all_fail_raises(self):
        with pytest.raises(TypeError, match="value"):
            from_json(WithUnion, {"value": [1, 2, 3]})


class TestLeafCoercion:
    def test_datetime(self):
        result = from_json(Record, _record_data())
        assert isinstance(result.created_at, datetime)
        assert result.created_at == datetime.fromisoformat("2026-08-05T12:34:56")

    def test_date(self):
        result = from_json(Record, _record_data())
        assert isinstance(result.day, date)
        assert result.day == date.fromisoformat("2026-08-05")

    def test_time(self):
        result = from_json(Record, _record_data())
        assert isinstance(result.when, time)
        assert result.when == time.fromisoformat("12:34:56")

    def test_uuid(self):
        result = from_json(Record, _record_data())
        assert isinstance(result.uid, UUID)
        assert result.uid == UUID("123e4567-e89b-12d3-a456-426614174000")

    def test_enum(self):
        result = from_json(Record, _record_data())
        assert result.role is Role.ADMIN

    def test_enum_by_value(self):
        assert from_json(Role, "user") is Role.USER

    def test_bool_rejected_for_int(self):
        with pytest.raises(TypeError, match="expected int"):
            from_json(User, {"id": True, "name": "ada"})

    def test_int_coerced_to_float(self):
        assert from_json(float, 3) == 3.0

    def test_bad_datetime_names_field(self):
        with pytest.raises(TypeError, match="created_at"):
            from_json(Record, {**_record_data(), "created_at": "not-a-date"})


class TestTopLevel:
    def test_top_level_list(self):
        result = from_json(list[User], [{"id": 1, "name": "ada"}])
        assert result == [User(id=1, name="ada")]
        assert isinstance(result[0], User)

    def test_top_level_scalar_int(self):
        assert from_json(int, 42) == 42

    def test_top_level_scalar_str(self):
        assert from_json(str, "hello") == "hello"

    def test_top_level_datetime(self):
        assert from_json(datetime, "2026-08-05T12:34:56") == datetime.fromisoformat("2026-08-05T12:34:56")

    def test_top_level_uuid(self):
        assert from_json(UUID, "123e4567-e89b-12d3-a456-426614174000") == UUID("123e4567-e89b-12d3-a456-426614174000")

    def test_top_level_enum(self):
        assert from_json(Role, "admin") is Role.ADMIN

    def test_top_level_dict(self):
        result = from_json(dict[str, User], {"a": {"id": 1, "name": "ada"}})
        assert isinstance(result["a"], User)

    def test_top_level_none_rejected(self):
        with pytest.raises(TypeError, match="expected"):
            from_json(User, None)


class TestErrorMessages:
    def test_error_names_field_and_expected_type(self):
        with pytest.raises(TypeError) as exc:
            from_json(User, {"id": 1, "name": 42})
        message = str(exc.value)
        assert "name" in message
        assert "str" in message

    def test_error_names_nested_path(self):
        with pytest.raises(TypeError) as exc:
            from_json(Team, {"name": "core", "members": [{"id": "x", "name": "ada"}]})
        message = str(exc.value)
        assert "members[0].id" in message
        assert "int" in message


class TestTypedResponseError:
    def test_is_plain_exception(self):
        from webcompy.exception import WebComPyException

        assert issubclass(TypedResponseError, Exception)
        assert not issubclass(TypedResponseError, WebComPyException)


def _record_data() -> dict:
    return {
        "created_at": "2026-08-05T12:34:56",
        "day": "2026-08-05",
        "when": "12:34:56",
        "uid": "123e4567-e89b-12d3-a456-426614174000",
        "role": "admin",
    }
