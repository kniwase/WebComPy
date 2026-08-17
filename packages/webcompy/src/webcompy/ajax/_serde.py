from __future__ import annotations

import types
from collections.abc import Mapping
from dataclasses import MISSING, InitVar, fields, is_dataclass
from datetime import date, datetime, time
from enum import Enum
from typing import Any, TypeVar, Union, get_args, get_origin, get_type_hints
from uuid import UUID

from webcompy.hydration._transfer_meta import apply_transfer_meta

T = TypeVar("T")


class TypedResponseError(Exception):
    pass


# Per-class resolved-hints cache. Both runtimes use a single-threaded event loop, so no lock is needed.
_hints_cache: dict[type, dict[str, Any]] = {}


def _type_hints(cls: type) -> dict[str, Any]:
    cached = _hints_cache.get(cls)
    if cached is None:
        resolved = get_type_hints(cls)
        _hints_cache[cls] = resolved
        return resolved
    return cached


def from_json(cls: type[T], data: Any, *, strict: bool = False, meta: Mapping[str, str] | None = None) -> T:
    if meta:
        data = apply_transfer_meta(data, meta, strict=strict)
    return _convert(cls, data, path=_type_name(cls), strict=strict)


def _type_name(tp: Any) -> str:
    if isinstance(tp, type):
        return tp.__name__
    return str(tp)


def _expected_type_name(tp: Any) -> str:
    if isinstance(tp, type):
        return tp.__name__
    if get_origin(tp) is not None:
        return str(tp)
    return str(tp)


def _convert(tp: Any, value: Any, *, path: str, strict: bool) -> Any:
    if tp is Any:
        return value

    origin = get_origin(tp)

    if value is None:
        if (origin is Union or origin is types.UnionType) and type(None) in get_args(tp):
            return None
        if tp is type(None):
            return None
        raise TypeError(f"{path}: expected {_expected_type_name(tp)}, got None")

    if origin is Union or origin is types.UnionType:
        for arg in get_args(tp):
            if arg is type(None):
                continue
            try:
                return _convert(arg, value, path=path, strict=strict)
            except (TypeError, ValueError):
                continue
        raise TypeError(f"{path}: expected {_expected_type_name(tp)}, got {type(value).__name__}")

    if origin is list:
        if not isinstance(value, list):
            raise TypeError(f"{path}: expected {_expected_type_name(tp)}, got {type(value).__name__}")
        item_tp = get_args(tp)[0] if get_args(tp) else Any
        return [_convert(item_tp, item, path=f"{path}[{i}]", strict=strict) for i, item in enumerate(value)]

    if origin is dict:
        if not isinstance(value, dict):
            raise TypeError(f"{path}: expected {_expected_type_name(tp)}, got {type(value).__name__}")
        value_tp = get_args(tp)[1] if get_args(tp) else Any
        return {key: _convert(value_tp, item, path=f"{path}.{key}", strict=strict) for key, item in value.items()}

    if origin is set or origin is frozenset:
        if not isinstance(value, origin):
            raise TypeError(f"{path}: expected {_expected_type_name(tp)}, got {type(value).__name__}")
        item_tp = get_args(tp)[0] if get_args(tp) else Any
        return origin(_convert(item_tp, item, path=f"{path}[*]", strict=strict) for item in value)

    if origin is tuple:
        if not isinstance(value, tuple):
            raise TypeError(f"{path}: expected {_expected_type_name(tp)}, got {type(value).__name__}")
        args = get_args(tp)
        if not args:
            return value
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_convert(args[0], item, path=f"{path}[{i}]", strict=strict) for i, item in enumerate(value))
        if len(args) != len(value):
            raise TypeError(f"{path}: expected {len(args)}-tuple, got {len(value)} items")
        return tuple(
            _convert(arg, item, path=f"{path}[{i}]", strict=strict)
            for i, (arg, item) in enumerate(zip(args, value, strict=True))
        )

    if is_dataclass(tp) and isinstance(tp, type):
        if isinstance(value, tp):
            return value
        return _convert_dataclass(tp, value, path=path, strict=strict)

    return _convert_leaf(tp, value, path=path)


def _convert_dataclass(tp: type, value: Any, *, path: str, strict: bool) -> Any:
    if not isinstance(value, dict):
        raise TypeError(f"{path}: expected {_expected_type_name(tp)}, got {type(value).__name__}")

    hints = _type_hints(tp)
    field_names = {f.name for f in fields(tp)}
    initvar_names = {name for name, hint in hints.items() if isinstance(hint, InitVar)}
    known_names = field_names | initvar_names

    if strict:
        unknown = set(value) - known_names
        if unknown:
            raise TypeError(f"{path}: unknown field(s) {sorted(unknown)}")

    kwargs: dict[str, Any] = {}
    for f in fields(tp):
        if f.name not in value:
            if f.default is MISSING and f.default_factory is MISSING:
                raise TypeError(f"{path}.{f.name}: missing required field")
            continue
        kwargs[f.name] = _convert(hints[f.name], value[f.name], path=f"{path}.{f.name}", strict=strict)

    return tp(**kwargs)


def _convert_leaf(tp: Any, value: Any, *, path: str) -> Any:
    if not isinstance(tp, type):
        raise TypeError(f"{path}: unsupported annotation {_expected_type_name(tp)}")

    if issubclass(tp, Enum):
        if isinstance(value, tp):
            return value
        try:
            return tp(value)
        except ValueError as err:
            raise TypeError(f"{path}: expected {tp.__name__} value, got {value!r}") from err

    if tp is bool:
        if not isinstance(value, bool):
            raise TypeError(f"{path}: expected bool, got {type(value).__name__}")
        return value

    if tp is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{path}: expected int, got {type(value).__name__}")
        return value

    if tp is float:
        if isinstance(value, bool):
            raise TypeError(f"{path}: expected float, got bool")
        if isinstance(value, int):
            return float(value)
        if not isinstance(value, float):
            raise TypeError(f"{path}: expected float, got {type(value).__name__}")
        return value

    if tp is str:
        if not isinstance(value, str):
            raise TypeError(f"{path}: expected str, got {type(value).__name__}")
        return value

    if tp is datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError as err:
                raise TypeError(f"{path}: expected ISO-8601 datetime string, got {value!r}") from err
        raise TypeError(f"{path}: expected datetime, got {type(value).__name__}")

    if tp is date:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError as err:
                raise TypeError(f"{path}: expected ISO-8601 date string, got {value!r}") from err
        raise TypeError(f"{path}: expected date, got {type(value).__name__}")

    if tp is time:
        if isinstance(value, time):
            return value
        if isinstance(value, str):
            try:
                return time.fromisoformat(value)
            except ValueError as err:
                raise TypeError(f"{path}: expected ISO-8601 time string, got {value!r}") from err
        raise TypeError(f"{path}: expected time, got {type(value).__name__}")

    if tp is UUID:
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError as err:
                raise TypeError(f"{path}: expected UUID string, got {value!r}") from err
        raise TypeError(f"{path}: expected UUID, got {type(value).__name__}")

    if isinstance(value, tp):
        return value

    raise TypeError(f"{path}: expected {_expected_type_name(tp)}, got {type(value).__name__}")
