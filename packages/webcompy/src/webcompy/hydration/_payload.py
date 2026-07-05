from __future__ import annotations

import base64
import html as html_module
import json
import zlib
from dataclasses import dataclass, field
from logging import getLogger
from typing import Any

from webcompy.hydration._codec import _FailureFlag, decode, encode

_logger = getLogger(__name__)


@dataclass
class TransferFetchEntry:
    status_code: int
    headers: dict[str, str]
    body: str


@dataclass
class TransferAsyncResultEntry:
    state: str = "success"
    data: Any = None


@dataclass
class TransferPayload:
    __webcompy_transfer_version__: int = 2
    fetches: dict[str, TransferFetchEntry] = field(default_factory=dict)
    async_results: dict[str, TransferAsyncResultEntry] = field(default_factory=dict)
    signals: dict[str, dict[str, Any]] = field(default_factory=dict)


_SUPPORTED_VERSIONS: frozenset[int] = frozenset({1, 2})
CURRENT_TRANSFER_VERSION: int = 2
DEFAULT_COMPRESSION_THRESHOLD: int = 1024


_COMPRESSED_FLAG_KEY: str = "__webcompy_compressed__"


def _try_serialize_value(value: Any) -> Any:
    if value is None:
        return None
    flag = _FailureFlag()
    encoded = encode(value, _flag=flag)
    if flag.failed:
        return None
    if encoded is None:
        return None
    return encoded


def _to_serializable(payload: TransferPayload) -> dict[str, Any]:
    return {
        "__webcompy_transfer_version__": payload.__webcompy_transfer_version__,
        "fetches": {
            url: {
                "status_code": entry.status_code,
                "headers": entry.headers,
                "body": entry.body,
            }
            for url, entry in payload.fetches.items()
        },
        "async_results": {
            cid: {
                "state": entry.state,
                "data": entry.data,
            }
            for cid, entry in payload.async_results.items()
        },
        "signals": {
            cid: {attr_name: value for attr_name, value in signals.items()} for cid, signals in payload.signals.items()
        },
    }


def _maybe_compress(json_str: str, version: int, compression_threshold: int | None) -> str:
    if compression_threshold is None or compression_threshold <= 0:
        return json_str
    if len(json_str.encode("utf-8")) <= compression_threshold:
        return json_str
    compressed = zlib.compress(json_str.encode("utf-8"))
    encoded = base64.b64encode(compressed).decode("ascii")
    envelope = {
        _COMPRESSED_FLAG_KEY: True,
        "__webcompy_transfer_version__": version,
        "data": encoded,
    }
    return json.dumps(envelope, ensure_ascii=False)


def serialize_payload(
    payload: TransferPayload,
    compression_threshold: int | None = DEFAULT_COMPRESSION_THRESHOLD,
) -> str:
    raw = _to_serializable(payload)
    cleaned_fetches: dict[str, dict[str, Any]] = {}
    for url, entry in raw["fetches"].items():
        serializable_body = _try_serialize_value(entry["body"])
        if serializable_body is None and entry["body"] is not None:
            _logger.warning("Excluding fetch %s: body is not encodable", url)
            continue
        cleaned_fetches[url] = {
            "status_code": entry["status_code"],
            "headers": entry["headers"],
            "body": serializable_body,
        }
    raw["fetches"] = cleaned_fetches
    cleaned_async_results: dict[str, dict[str, Any]] = {}
    for cid, entry in raw["async_results"].items():
        serializable_data = _try_serialize_value(entry["data"])
        if serializable_data is None:
            _logger.warning("Excluding async_result %s: data is not encodable", cid)
            continue
        cleaned_async_results[cid] = {
            "state": entry["state"],
            "data": serializable_data,
        }
    raw["async_results"] = cleaned_async_results
    cleaned_signals: dict[str, dict[str, Any]] = {}
    for cid, attrs in raw["signals"].items():
        cleaned_signals[cid] = {}
        for attr_name, raw_value in attrs.items():
            serializable_data = _try_serialize_value(raw_value)
            if serializable_data is None:
                _logger.warning(
                    "Excluding signal %s.%s: value is not encodable",
                    cid,
                    attr_name,
                )
                continue
            cleaned_signals[cid][attr_name] = serializable_data
        if not cleaned_signals[cid]:
            cleaned_signals.pop(cid, None)
    raw["signals"] = cleaned_signals
    dumped = json.dumps(raw, ensure_ascii=False)
    serialized = _maybe_compress(dumped, payload.__webcompy_transfer_version__, compression_threshold)
    escaped = html_module.escape(serialized, quote=True)
    return escaped


def _decompress_raw(raw: dict[str, Any]) -> dict[str, Any] | None:
    data = raw.get("data")
    if not isinstance(data, str):
        _logger.warning("Compressed payload missing 'data' field")
        return None
    try:
        decoded = base64.b64decode(data)
        decompressed = zlib.decompress(decoded)
        json_str = decompressed.decode("utf-8")
    except (ValueError, zlib.error, UnicodeDecodeError):
        _logger.warning("Failed to decompress payload")
        return None
    try:
        inner = json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        _logger.warning("Failed to parse decompressed payload")
        return None
    if not isinstance(inner, dict):
        _logger.warning("Decompressed payload is not a dict")
        return None
    return inner


def deserialize_payload(text: str) -> TransferPayload | None:
    try:
        unescaped = html_module.unescape(text)
        raw = json.loads(unescaped)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    if raw.get(_COMPRESSED_FLAG_KEY) is True:
        raw = _decompress_raw(raw)
        if raw is None:
            return None
        if not isinstance(raw, dict):
            return None
    version = raw.get("__webcompy_transfer_version__")
    if version not in _SUPPORTED_VERSIONS:
        return None
    raw = decode(raw)
    fetches_data = raw.get("fetches") or {}
    async_results_data = raw.get("async_results") or {}
    signals_data = raw.get("signals") or {}
    fetches: dict[str, TransferFetchEntry] = {}
    for url, entry in fetches_data.items():
        if not isinstance(entry, dict):
            continue
        fetches[url] = TransferFetchEntry(
            status_code=entry.get("status_code", 200),
            headers=entry.get("headers", {}),
            body=entry.get("body", ""),
        )
    async_results: dict[str, TransferAsyncResultEntry] = {}
    for cid, entry in async_results_data.items():
        if not isinstance(entry, dict):
            continue
        async_results[cid] = TransferAsyncResultEntry(
            state=entry.get("state", "success"),
            data=entry.get("data"),
        )
    signals: dict[str, dict[str, Any]] = {}
    if version == 2:
        for cid, attrs in signals_data.items():
            if not isinstance(attrs, dict):
                continue
            signals[cid] = {attr_name: value for attr_name, value in attrs.items()}
    return TransferPayload(
        __webcompy_transfer_version__=version,
        fetches=fetches,
        async_results=async_results,
        signals=signals,
    )
