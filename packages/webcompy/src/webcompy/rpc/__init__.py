"""Client-side JSON-RPC contracts, transports, and streaming helpers."""

from __future__ import annotations

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
from webcompy.rpc._registry import ProcedureRegistry
from webcompy.rpc._stream import RpcStream, RpcStreamState
from webcompy.rpc._ws_client import RpcSubscription, RpcSubscriptionState, RpcWsClient

__all__ = [
    "Procedure",
    "ProcedureRegistry",
    "RpcCall",
    "RpcError",
    "RpcHttpClient",
    "RpcStream",
    "RpcStreamState",
    "RpcSubscription",
    "RpcSubscriptionState",
    "RpcTransport",
    "RpcWsClient",
    "StreamingProcedure",
    "Subscription",
    "batch",
    "notify",
]
