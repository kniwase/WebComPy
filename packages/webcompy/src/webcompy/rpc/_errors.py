"""JSON-RPC 2.0 error codes and the ``RpcError`` exception."""

from __future__ import annotations

from typing import Any

from webcompy.exception import WebComPyException

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
SERVER_ERROR = -32000


class RpcError(WebComPyException):
    """A JSON-RPC error returned by the server or raised by the client.

    Args:
        code: JSON-RPC error code, e.g. ``SERVER_ERROR``.
        message: Human-readable error message.
        data: Optional error payload supplied by the server.

    Attributes:
        code: JSON-RPC error code carried by the error.
        message: Human-readable error message.
        data: Optional error payload; ``None`` when absent.

    """

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(f"RPC error {code}: {message}")
        self.code = code
        self.message = message
        self.data = data


__all__ = [
    "INTERNAL_ERROR",
    "INVALID_PARAMS",
    "INVALID_REQUEST",
    "METHOD_NOT_FOUND",
    "PARSE_ERROR",
    "SERVER_ERROR",
    "RpcError",
]
