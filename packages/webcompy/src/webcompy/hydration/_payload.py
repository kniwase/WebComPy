from __future__ import annotations

import html as html_module
import json
from dataclasses import dataclass, field
from logging import getLogger
from typing import Any

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
    __webcompy_transfer_version__: int = 1
    fetches: dict[str, TransferFetchEntry] = field(default_factory=dict)
    async_results: dict[str, TransferAsyncResultEntry] = field(default_factory=dict)


_SUPPORTED_VERSION = 1


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
    }


def _try_serialize_value(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return None


def serialize_payload(payload: TransferPayload) -> str:
    raw = _to_serializable(payload)
    cleaned_async_results: dict[str, dict[str, Any]] = {}
    for cid, entry in raw["async_results"].items():
        serializable_data = _try_serialize_value(entry["data"])
        if serializable_data is None:
            _logger.warning("Excluding async_result %s: data is not JSON-serializable", cid)
            continue
        cleaned_async_results[cid] = {
            "state": entry["state"],
            "data": serializable_data,
        }
    raw["async_results"] = cleaned_async_results
    dumped = json.dumps(raw, ensure_ascii=False, default=str)
    escaped = html_module.escape(dumped, quote=True)
    return escaped


def deserialize_payload(text: str) -> TransferPayload | None:
    try:
        unescaped = html_module.unescape(text)
        raw = json.loads(unescaped)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    version = raw.get("__webcompy_transfer_version__")
    if version != _SUPPORTED_VERSION:
        return None
    fetches_data = raw.get("fetches") or {}
    async_results_data = raw.get("async_results") or {}
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
    return TransferPayload(
        __webcompy_transfer_version__=version,
        fetches=fetches,
        async_results=async_results,
    )
