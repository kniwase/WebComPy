"""RPC middleware: stackable processors around the HTTP JSON-RPC transports."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeAlias


@dataclass
class RpcBatchEntry:
    """One procedure invocation inside a batch dispatched through middleware.

    Attributes:
        method: RPC method name.
        params: Typed parameters before encoding; middleware MAY replace.
        result_type: Type the result is deserialized as.

    """

    method: str
    params: Any
    result_type: Any


@dataclass
class RpcContext:
    """Mutable view of an outgoing JSON-RPC operation handled by middleware.

    For single calls ``method``/``params``/``result_type`` describe the
    operation and ``is_batch`` is ``False``. For batch dispatches
    ``is_batch`` is ``True``, ``method`` is empty, and ``batch_entries``
    lists every invocation in order; middleware MAY replace any entry's
    ``params`` before the envelopes are encoded. ``headers`` starts empty
    and is merged onto the fixed transport headers.

    Args:
        method: RPC method name (empty for batches).
        params: Typed parameters before encoding.
        headers: Extra request headers contributed by middleware.
        result_type: Type the result is deserialized as.
        is_batch: Whether this context wraps a batch dispatch.
        batch_entries: Per-invocation view when ``is_batch`` is ``True``.

    Attributes:
        method: RPC method name (empty for batches).
        params: Typed parameters before encoding.
        headers: Extra request headers contributed by middleware.
        result_type: Type the result is deserialized as.
        is_batch: Whether this context wraps a batch dispatch.
        batch_entries: Per-invocation view when ``is_batch`` is ``True``.

    """

    method: str = ""
    params: Any = None
    headers: dict[str, str] = field(default_factory=dict)
    result_type: Any = None
    is_batch: bool = False
    batch_entries: list[RpcBatchEntry] | None = None


class RpcNext(Protocol):
    """Invokes the next middleware layer or the terminal dispatch.

    Calling with only ``ctx`` proceeds normally. Supplying ``response``
    short-circuits the network round trip: the fragment (a ``dict`` with
    ``result``/``meta`` members for calls, a ``list`` of such dicts for
    batches, or a ``FetchStream`` for streaming calls) is normalized and
    routed through the standard validation path, so schema guarantees hold.
    """

    def __call__(
        self,
        ctx: RpcContext | None = None,
        *,
        response: Any = None,
        stream: Any = None,
    ) -> Awaitable[Any]: ...


RpcMiddleware: TypeAlias = Callable[[RpcContext, RpcNext], Awaitable[Any]]


class RpcMiddlewareRegistry:
    """Ordered, additively mutated collection of RPC middlewares.

    One instance is provided per render context under
    ``RPC_MIDDLEWARE_KEY``. Middlewares are consulted at each operation,
    so registrations made after installation take effect on subsequent
    calls.

    """

    def __init__(self) -> None:
        self._middlewares: list[RpcMiddleware] = []

    def use(self, middleware: RpcMiddleware) -> None:
        """Append *middleware* to the registry.

        Args:
            middleware: Async callable invoked with the operation context
                and a ``next`` callable.

        """
        self._middlewares.append(middleware)

    @property
    def middlewares(self) -> tuple[RpcMiddleware, ...]:
        """Snapshot of registered middlewares in registration order.

        Returns:
            Middlewares ordered so index ``0`` is the outermost layer.

        """
        return tuple(self._middlewares)


def merge_extra_headers(extra: dict[str, str] | None) -> dict[str, str]:
    """Merge middleware-contributed headers onto the fixed transport headers.

    ``Content-Type`` is forced back to ``application/json`` after merging
    so middleware cannot break the JSON-RPC wire format.

    Args:
        extra: Headers contributed by middleware, or ``None``.

    Returns:
        The merged header mapping ready for the fetch boundary.

    """
    merged: dict[str, str] = {"Content-Type": "application/json"}
    if extra:
        merged.update(extra)
    merged["Content-Type"] = "application/json"
    return merged


async def run_rpc_middlewares(
    middlewares: tuple[RpcMiddleware, ...],
    ctx: RpcContext,
    terminal: Callable[[RpcContext], Awaitable[Any]],
    synthesize: Callable[[Any, RpcContext], Awaitable[Any]],
) -> Any:
    """Run ``ctx`` through ``middlewares`` around ``terminal``.

    Index ``0`` runs outermost. A middleware that supplies ``response``
    skips the remaining layers and the terminal dispatch; the supplied
    value is routed through ``synthesize`` so validation still applies.

    Args:
        middlewares: Ordered middleware snapshot.
        ctx: Operation context handed to the first middleware.
        terminal: Dispatches the (possibly mutated) context.
        synthesize: Validates and materializes an intercepted response.

    Returns:
        The value produced by the outermost layer.

    """
    if not middlewares:
        return await terminal(ctx)

    async def run(index: int, context: RpcContext, *, response: Any = None) -> Any:
        if response is not None:
            return await synthesize(response, context)
        if index == len(middlewares):
            return await terminal(context)
        middleware = middlewares[index]

        async def nxt(ctx: RpcContext | None = None, *, response: Any = None, stream: Any = None) -> Any:
            supplied = response if response is not None else stream
            return await run(index + 1, ctx if ctx is not None else context, response=supplied)

        return await middleware(context, nxt)

    return await run(0, ctx)
