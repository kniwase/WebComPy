from __future__ import annotations

import base64
import copy
import dataclasses
import logging
from collections.abc import Callable, Mapping
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from webcompy.exception import WebComPyException

_logger = logging.getLogger(__name__)

META_HEADER_NAME = "X-WebComPy-Transfer-Meta"
META_BODY_KEY = "__webcompy_transfer_meta__"


def encode_with_meta(value: Any) -> tuple[Any, dict[str, str]]:
    meta: dict[str, str] = {}
    json_data = _encode_value(value, path="", meta=meta, _seen=set())
    return json_data, meta


def merge_meta_into_body(json_data: Any, meta: Mapping[str, str]) -> dict[str, Any]:
    if not isinstance(json_data, dict):
        raise WebComPyException(
            "Body transfer mode requires a top-level JSON object payload, got "
            f"{type(json_data).__name__}. Use header mode, or restructure the payload as an object."
        )
    return {**json_data, META_BODY_KEY: dict(meta)}


def apply_transfer_meta(data: Any, meta: Mapping[str, str] | None, *, strict: bool = False) -> Any:
    if not meta:
        return data
    result = copy.deepcopy(data)
    for path, tag in sorted(meta.items(), key=lambda item: item[0].count("/"), reverse=True):
        segments = _resolve_segments(path)
        if not segments:
            result = _decode_tagged(tag, result, strict=strict, path=path)
            continue
        node: Any = result
        for segment in segments[:-1]:
            node = _navigate(node, segment, path=path)
        leaf_segment = segments[-1]
        if isinstance(node, dict):
            if leaf_segment not in node:
                raise ValueError(f"Transfer meta path {path!r} does not exist in response data")
            node[leaf_segment] = _decode_tagged(tag, node[leaf_segment], strict=strict, path=path)
        elif isinstance(node, list):
            if not leaf_segment.isdigit():
                raise ValueError(f"Transfer meta path {path!r} does not exist in response data")
            try:
                node[int(leaf_segment)] = _decode_tagged(tag, node[int(leaf_segment)], strict=strict, path=path)
            except IndexError:
                raise ValueError(f"Transfer meta path {path!r} does not exist in response data") from None
        else:
            raise ValueError(f"Transfer meta path {path!r} does not exist in response data")
    return result


def _encode_value(value: Any, *, path: str, meta: dict[str, str], _seen: set[int]) -> Any:
    if value is None or (isinstance(value, (bool, int, float, str)) and not isinstance(value, Enum)):
        return value

    obj_id = id(value)
    if obj_id in _seen:
        raise WebComPyException(f"Circular reference detected while encoding value at path {path!r}")
    _seen.add(obj_id)
    try:
        if isinstance(value, dict):
            return {
                k: _encode_value(v, path=f"{path}/{_escape_token(str(k))}", meta=meta, _seen=_seen)
                for k, v in value.items()
            }

        if isinstance(value, list):
            return [_encode_value(v, path=f"{path}/{i}", meta=meta, _seen=_seen) for i, v in enumerate(value)]

        if isinstance(value, datetime):
            meta[path] = "datetime"
            return value.isoformat()
        if isinstance(value, date):
            meta[path] = "date"
            return value.isoformat()
        if isinstance(value, time):
            meta[path] = "time"
            return value.isoformat()
        if isinstance(value, frozenset):
            meta[path] = "frozenset"
            return [_encode_value(v, path=f"{path}/{i}", meta=meta, _seen=_seen) for i, v in enumerate(value)]
        if isinstance(value, set):
            meta[path] = "set"
            return [_encode_value(v, path=f"{path}/{i}", meta=meta, _seen=_seen) for i, v in enumerate(value)]
        if isinstance(value, bytes):
            meta[path] = "bytes"
            return base64.b64encode(value).decode("ascii")
        if isinstance(value, Decimal):
            meta[path] = "decimal"
            return str(value)
        if isinstance(value, tuple):
            meta[path] = "tuple"
            return [_encode_value(v, path=f"{path}/{i}", meta=meta, _seen=_seen) for i, v in enumerate(value)]
        if isinstance(value, Path):
            meta[path] = "path"
            return str(value)
        if isinstance(value, UUID):
            meta[path] = "uuid"
            return str(value)
        if isinstance(value, Enum):
            return _encode_value(value.value, path=path, meta=meta, _seen=_seen)

        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            return _encode_value(model_dump(), path=path, meta=meta, _seen=_seen)

        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return {
                f.name: _encode_value(
                    getattr(value, f.name),
                    path=f"{path}/{_escape_token(f.name)}",
                    meta=meta,
                    _seen=_seen,
                )
                for f in dataclasses.fields(value)
            }

        raise WebComPyException(f"Cannot encode value of type {type(value).__name__} at path {path!r}")
    finally:
        _seen.discard(obj_id)


def _escape_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _resolve_segments(path: str) -> list[str]:
    if path == "":
        return []
    if not path.startswith("/"):
        raise ValueError(f"Invalid transfer meta path {path!r}: expected a JSON Pointer")
    return [_unescape_token(segment) for segment in path[1:].split("/")]


def _unescape_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _navigate(node: Any, segment: str, *, path: str) -> Any:
    if isinstance(node, dict):
        if segment not in node:
            raise ValueError(f"Transfer meta path {path!r} does not exist in response data")
        return node[segment]
    if isinstance(node, list):
        if not segment.isdigit():
            raise ValueError(f"Transfer meta path {path!r} does not exist in response data")
        try:
            return node[int(segment)]
        except IndexError:
            raise ValueError(f"Transfer meta path {path!r} does not exist in response data") from None
    raise ValueError(f"Transfer meta path {path!r} does not exist in response data")


def _decode_tagged(tag: str, value: Any, *, strict: bool, path: str) -> Any:
    decoder = _DECODERS.get(tag)
    if decoder is None:
        if strict:
            raise ValueError(f"Unknown transfer meta tag {tag!r} at path {path!r}")
        _logger.warning("Unknown transfer meta tag %r at path %r; leaving value as-is", tag, path)
        return value
    try:
        return decoder(value)
    except (TypeError, ValueError) as err:
        raise ValueError(f"Failed to decode value for transfer meta tag {tag!r} at path {path!r}") from err


def _decode_bytes(value: Any) -> Any:
    if not isinstance(value, str):
        raise TypeError("expected base64 string")
    return base64.b64decode(value)


def _decode_set(value: Any) -> Any:
    if not isinstance(value, list):
        raise TypeError("expected array")
    return set(value)


def _decode_frozenset(value: Any) -> Any:
    if not isinstance(value, list):
        raise TypeError("expected array")
    return frozenset(value)


def _decode_tuple(value: Any) -> Any:
    if not isinstance(value, list):
        raise TypeError("expected array")
    return tuple(value)


def _decode_decimal(value: Any) -> Any:
    if not isinstance(value, (str, int, float)):
        raise TypeError("expected string or number")
    return Decimal(str(value))


def _decode_isoformat(cls: Callable[[str], Any]) -> Callable[[Any], Any]:
    def decode(value: Any) -> Any:
        if not isinstance(value, str):
            raise TypeError("expected ISO string")
        return cls(value)

    return decode


def _decode_uuid(value: Any) -> Any:
    if not isinstance(value, str):
        raise TypeError("expected UUID string")
    return UUID(value)


def _decode_path(value: Any) -> Any:
    if not isinstance(value, str):
        raise TypeError("expected path string")
    return Path(value)


_DECODERS: dict[str, Callable[[Any], Any]] = {
    "datetime": _decode_isoformat(datetime.fromisoformat),
    "date": _decode_isoformat(date.fromisoformat),
    "time": _decode_isoformat(time.fromisoformat),
    "set": _decode_set,
    "frozenset": _decode_frozenset,
    "bytes": _decode_bytes,
    "decimal": _decode_decimal,
    "tuple": _decode_tuple,
    "path": _decode_path,
    "uuid": _decode_uuid,
}
