from __future__ import annotations

from webcompy.rpc._client import batch, call, notify
from webcompy.rpc._errors import RpcError
from webcompy.rpc._registry import ProcedureRegistry

__all__ = [
    "ProcedureRegistry",
    "RpcError",
    "batch",
    "call",
    "notify",
]
