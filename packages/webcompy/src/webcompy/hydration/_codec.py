from __future__ import annotations

import base64
import dataclasses
import importlib
from collections.abc import Callable
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from logging import getLogger
from pathlib import Path
from typing import Any
from uuid import UUID

_logger = getLogger(__name__)


_TYPE_TAG_KEY = "__webcompy_type__"
_VALUE_KEY = "__webcompy_value__"


_type_handlers: dict[type, tuple[str, Callable[[Any], Any], Callable[[Any], Any]]] = {}
_type_handlers_by_name: dict[str, Callable[[Any], Any]] = {}


def _qualified_type_name(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def register_type_handler(
    cls: type,
    encoder: Callable[[Any], Any],
    decoder: Callable[[Any], Any],
) -> None:
    type_name = _qualified_type_name(cls)
    _type_handlers[cls] = (type_name, encoder, decoder)
    _type_handlers_by_name[type_name] = decoder


def _tag(type_name: str, payload: Any) -> dict[str, Any]:
    return {_TYPE_TAG_KEY: type_name, _VALUE_KEY: payload}


def _decode_builtin(type_name: str, payload: Any) -> Any:
    if type_name == "datetime":
        return datetime.fromisoformat(payload)
    if type_name == "date":
        return date.fromisoformat(payload)
    if type_name == "time":
        return time.fromisoformat(payload)
    if type_name == "set":
        return set(decode(v) for v in payload)
    if type_name == "frozenset":
        return frozenset(decode(v) for v in payload)
    if type_name == "bytes":
        return base64.b64decode(payload)
    if type_name == "decimal":
        return Decimal(str(payload))
    if type_name == "tuple":
        return tuple(decode(v) for v in payload)
    if type_name == "path":
        return Path(str(payload))
    if type_name == "uuid":
        return UUID(str(payload))
    if type_name == "enum":
        return _reconstruct_qualified(payload, reconstruct_enum)
    if type_name == "dataclass":
        return _reconstruct_qualified(payload, reconstruct_dataclass)
    _logger.warning("Unknown __webcompy_type__: %r", type_name)
    return None


def _resolve_class(module_name: str, class_name: str) -> type | None:
    for cls, _ in _type_handlers.items():
        if cls.__name__ == class_name and cls.__module__ == module_name:
            return cls
    try:
        module = importlib.import_module(module_name)
    except Exception:
        _logger.exception("Failed to import %s for decode", module_name)
        return None
    try:
        return getattr(module, class_name)
    except AttributeError:
        _logger.exception("Module %s has no attribute %s", module_name, class_name)
        return None


def reconstruct_enum(cls: type, payload: Any) -> Any:
    if not isinstance(payload, dict):
        return None
    value = payload.get("value")
    try:
        return cls(value)
    except Exception:
        _logger.exception("Failed to reconstruct enum %s", cls.__name__)
        return None


def reconstruct_dataclass(cls: type, payload: Any) -> Any:
    if not isinstance(payload, dict):
        return None
    fields = payload.get("fields", {})
    if not isinstance(fields, dict):
        return None
    try:
        return cls(**{k: decode(v) for k, v in fields.items()})
    except Exception:
        _logger.exception("Failed to reconstruct dataclass %s", cls.__name__)
        return None


def _reconstruct_qualified(payload: Any, reconstruct: Callable[[type, Any], Any]) -> Any:
    if not isinstance(payload, dict):
        return None
    module_name = payload.get("module")
    class_name = payload.get("name")
    if not isinstance(module_name, str) or not isinstance(class_name, str):
        return None
    cls = _resolve_class(module_name, class_name)
    if cls is None:
        return None
    return reconstruct(cls, payload)


_BUILTIN_DECODERS: dict[str, Callable[[Any], Any]] = {
    name: (lambda payload, _name=name: _decode_builtin(_name, payload))
    for name in (
        "datetime",
        "date",
        "time",
        "set",
        "frozenset",
        "bytes",
        "decimal",
        "tuple",
        "path",
        "uuid",
        "enum",
        "dataclass",
    )
}


_SENTINEL = object()


def _encode_builtin(value: Any) -> Any:
    if isinstance(value, datetime):
        return _tag("datetime", value.isoformat())
    if isinstance(value, date) and not isinstance(value, datetime):
        return _tag("date", value.isoformat())
    if isinstance(value, time):
        return _tag("time", value.isoformat())
    if isinstance(value, frozenset):
        return _tag("frozenset", [encode(v) for v in value])
    if isinstance(value, set):
        return _tag("set", [encode(v) for v in value])
    if isinstance(value, bytes):
        return _tag("bytes", base64.b64encode(value).decode("ascii"))
    if isinstance(value, Decimal):
        return _tag("decimal", str(value))
    if isinstance(value, tuple):
        return _tag("tuple", [encode(v) for v in value])
    if isinstance(value, Path):
        return _tag("path", str(value))
    if isinstance(value, UUID):
        return _tag("uuid", str(value))
    if isinstance(value, Enum):
        cls = type(value)
        return _tag(
            "enum",
            {
                "module": cls.__module__,
                "name": cls.__name__,
                "value": value.value,
            },
        )
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        cls = type(value)
        return _tag(
            "dataclass",
            {
                "module": cls.__module__,
                "name": cls.__name__,
                "fields": {f.name: encode(getattr(value, f.name)) for f in dataclasses.fields(value)},
            },
        )
    return _SENTINEL


class _FailureFlag:
    failed: bool = False


def encode(
    value: Any,
    _seen: set[int] | None = None,
    _flag: _FailureFlag | None = None,
) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    if _seen is None:
        _seen = set()
    obj_id = id(value)
    if obj_id in _seen:
        _logger.warning("Circular reference detected in transfer value; dropping.")
        if _flag is not None:
            _flag.failed = True
        return None
    _seen.add(obj_id)
    try:
        if isinstance(value, dict):
            if _TYPE_TAG_KEY in value:
                _logger.warning(
                    "Reserved key %r detected in user dict; encode behavior is undefined.",
                    _TYPE_TAG_KEY,
                )
            return {k: encode(v, _seen, _flag) for k, v in value.items()}

        if isinstance(value, list):
            return [encode(v, _seen, _flag) for v in value]

        for cls, (type_name, encoder, _) in _type_handlers.items():
            if isinstance(value, cls):
                return _tag(type_name, encoder(value))

        result = _encode_builtin(value)
        if result is not _SENTINEL:
            return result

        _logger.warning(
            "Cannot encode value of type %s; dropping.",
            type(value).__name__,
        )
        if _flag is not None:
            _flag.failed = True
        return None
    finally:
        _seen.discard(obj_id)


def _decode_type_tag(value: dict[str, Any]) -> Any:
    type_name = value.get(_TYPE_TAG_KEY)
    if not isinstance(type_name, str):
        return value

    payload = value.get(_VALUE_KEY)
    decoder = _BUILTIN_DECODERS.get(type_name)
    if decoder is None:
        decoder = _type_handlers_by_name.get(type_name)
    if decoder is None:
        _logger.warning("Unknown __webcompy_type__: %r", type_name)
        return None
    try:
        return decoder(payload)
    except Exception:
        _logger.exception("Failed to decode __webcompy_type__=%r", type_name)
        return None


def decode(value: Any) -> Any:
    if isinstance(value, dict):
        if _TYPE_TAG_KEY in value:
            return _decode_type_tag(value)
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value
