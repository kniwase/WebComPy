"""Client-side JSON-RPC contracts, transports, and streaming helpers."""

from __future__ import annotations

from webcompy.di._keys import RPC_MIDDLEWARE_KEY
from webcompy.rpc._contracts import (
    Procedure,
    RpcCall,
    RpcHttpClient,
    RpcTransport,
    StreamingProcedure,
    Subscription,
    batch,
    notify,
)
from webcompy.rpc._errors import RpcError
from webcompy.rpc._middleware import (
    RpcBatchEntry,
    RpcContext,
    RpcMiddleware,
    RpcMiddlewareRegistry,
    add_rpc_middleware,
)
from webcompy.rpc._registry import ProcedureRegistry
from webcompy.rpc._stream import RpcStream, RpcStreamState
from webcompy.rpc._ws_client import RpcSubscription, RpcSubscriptionState, RpcWsClient

__all__ = [
    "RPC_MIDDLEWARE_KEY",
    "Procedure",
    "ProcedureRegistry",
    "RpcBatchEntry",
    "RpcCall",
    "RpcContext",
    "RpcError",
    "RpcHttpClient",
    "RpcMiddleware",
    "RpcMiddlewareRegistry",
    "RpcStream",
    "RpcStreamState",
    "RpcSubscription",
    "RpcSubscriptionState",
    "RpcTransport",
    "RpcWsClient",
    "StreamingProcedure",
    "Subscription",
    "add_rpc_middleware",
    "batch",
    "notify",
]
