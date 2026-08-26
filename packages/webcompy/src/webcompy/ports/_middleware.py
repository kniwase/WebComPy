"""Fetch middleware: stackable request/response processors around ``FetchPort``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, TypeAlias, cast

from webcompy.ports._fetch import FetchPort, FetchStream, Response


@dataclass
class FetchRequest:
    """Mutable view of an outgoing HTTP request handled by fetch middleware.

    Middleware MAY mutate any field in place, or hand a replacement
    ``FetchRequest`` to ``next``, before invoking the next layer.

    Args:
        url: Target URL.
        method: HTTP method.
        headers: Mutable request headers, or ``None``.
        body: Request body as text or bytes, or ``None``.

    Attributes:
        url: Target URL.
        method: HTTP method.
        headers: Mutable request headers, or ``None``.
        body: Request body as text or bytes, or ``None``.

    """

    url: str
    method: str
    headers: dict[str, str] | None
    body: str | bytes | None


class FetchNext(Protocol):
    """Invokes the next middleware layer or the terminal dispatch.

    Calling with only ``request`` proceeds normally. Supplying ``response``
    short-circuits every remaining layer and the inner port: the supplied
    object becomes the result of the operation without any network access.
    On the streaming path the supplied object is a ``FetchStream`` whose
    metadata is already committed.

    """

    def __call__(
        self,
        request: FetchRequest,
        *,
        response: Response | FetchStream | None = None,
    ) -> Awaitable[Response | FetchStream]: ...


FetchMiddleware: TypeAlias = Callable[
    [FetchRequest, FetchNext],
    Awaitable["Response | FetchStream"],
]
"""Async callable that wraps one fetch or streaming HTTP request.

Receives the mutable request view and a ``next`` handle whose
synthetic ``response`` short-circuits the inner port. Middleware at
index ``0`` runs outermost.

"""


class FetchMiddlewareRegistry:
    """Ordered, additively mutated collection of fetch middlewares.

    One instance is provided per render context under
    ``FETCH_MIDDLEWARE_KEY``. ``use`` appends a middleware and advances
    ``generation`` so an installed chain wrapper can rebuild its cached
    sub-chains lazily on the next request.

    """

    def __init__(self) -> None:
        self._middlewares: list[FetchMiddleware] = []
        self._generation: int = 0

    def use(self, middleware: FetchMiddleware) -> None:
        """Append *middleware* to the registry and advance ``generation``.

        Args:
            middleware: Async callable invoked with the request view and a
                ``next`` callable.

        """
        self._middlewares.append(middleware)
        self._generation += 1

    @property
    def middlewares(self) -> tuple[FetchMiddleware, ...]:
        """Snapshot of registered middlewares in registration order.

        Returns:
            Middlewares ordered so index ``0`` is the outermost layer.

        """
        return tuple(self._middlewares)

    @property
    def generation(self) -> int:
        """Counter advanced on every registration.

        Returns:
            Current generation value.

        """
        return self._generation


async def _dispatch_fetch(inner: FetchPort, request: FetchRequest) -> Response:
    return await inner.fetch(request.url, method=request.method, headers=request.headers, body=request.body)


async def _dispatch_stream(inner: FetchPort, request: FetchRequest) -> FetchStream:
    return await inner.stream(request.url, method=request.method, headers=request.headers, body=request.body)


def _make_head(
    middlewares: tuple[FetchMiddleware, ...],
    dispatcher: Callable[[FetchRequest], Awaitable[Any]],
) -> Callable[..., Awaitable[Any]]:
    """Compose ``middlewares`` around ``dispatcher`` with index 0 outermost."""

    async def run(index: int, request: FetchRequest, *, response: Any = None) -> Any:
        if response is not None:
            return response
        if index == len(middlewares):
            return await dispatcher(request)
        middleware = middlewares[index]

        async def nxt(request: FetchRequest = request, *, response: Response | FetchStream | None = None) -> Any:
            return await run(index + 1, request, response=response)

        return await middleware(request, nxt)

    async def head(request: FetchRequest, *, response: Any = None) -> Any:
        return await run(0, request, response=response)

    return head


class _MiddlewareFetchPort(FetchPort):
    """Wraps a concrete port in the registry's middleware chains.

    Sub-chains are rebuilt lazily whenever the registry ``generation``
    changes, so registrations made after installation take effect on
    subsequent requests. Internal port methods are delegated to the
    wrapped implementation.
    """

    def __init__(self, inner: FetchPort, registry: FetchMiddlewareRegistry) -> None:
        self._inner = inner
        self._registry = registry
        self._generation: int = -1
        self._fetch_head: Callable[..., Awaitable[Any]] = _make_head((), lambda req: _dispatch_fetch(inner, req))
        self._stream_head: Callable[..., Awaitable[Any]] = _make_head((), lambda req: _dispatch_stream(inner, req))

    def _ensure_chains(self) -> None:
        generation = self._registry.generation
        if self._generation == generation:
            return
        self._generation = generation
        middlewares = self._registry.middlewares
        inner = self._inner
        self._fetch_head = _make_head(middlewares, lambda req: _dispatch_fetch(inner, req))
        self._stream_head = _make_head(middlewares, lambda req: _dispatch_stream(inner, req))

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | bytes | None = None,
    ) -> Response:
        """Run the fetch chain for one buffered request.

        Args:
            url: Target URL.
            method: HTTP method.
            headers: Optional request headers.
            body: Optional request body as text or bytes.

        Returns:
            The response produced by the outermost middleware.

        """
        self._ensure_chains()
        result = await self._fetch_head(FetchRequest(url=url, method=method, headers=headers, body=body))
        return cast("Response", result)

    async def stream(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | bytes | None = None,
    ) -> FetchStream:
        """Run the streaming chain for one streamed request.

        Args:
            url: Target URL.
            method: HTTP method.
            headers: Optional request headers.
            body: Optional request body as text or bytes.

        Returns:
            The stream produced by the outermost middleware.

        """
        self._ensure_chains()
        result = await self._stream_head(FetchRequest(url=url, method=method, headers=headers, body=body))
        return cast("FetchStream", result)

    def is_self_site_url(self, url: str) -> bool:
        """Delegate classification to the wrapped port.

        Args:
            url: URL to classify.

        Returns:
            Whether the wrapped port treats *url* as self-site.

        """
        return self._inner.is_self_site_url(url)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the wrapped port.

        Args:
            name: Attribute name.

        Returns:
            The wrapped port's attribute.

        """
        return getattr(self._inner, name)

    @property
    def noop(self) -> bool:
        """Whether the wrapped port degrades streaming operations.

        Returns:
            The wrapped port's ``noop`` marker, ``False`` when absent.

        """
        return bool(getattr(self._inner, "noop", False))

    def populate_from_transfer(self, data: dict[str, Any]) -> None:
        """Seed the wrapped browser port's hydration cache.

        Args:
            data: Transfer entries deserialized from the hydration payload.

        """
        delegate = getattr(self._inner, "populate_from_transfer", None)
        if delegate is not None:
            delegate(data)

    def get_transfer_data(self) -> dict[str, Any]:
        """Collect transferable responses from the wrapped server port.

        Returns:
            Transfer entries keyed like the wrapped port produces; empty
            when the wrapped port does not support transfer collection.

        """
        delegate = getattr(self._inner, "get_transfer_data", None)
        if delegate is None:
            return {}
        return delegate()

    def clear_cache(self) -> None:
        """Clear the wrapped port's response cache when supported."""
        delegate = getattr(self._inner, "clear_cache", None)
        if delegate is not None:
            delegate()

    def close(self) -> Any:
        """Close the wrapped port when supported.

        Returns:
            Whatever the wrapped port's ``close`` returns (possibly a
            coroutine for server implementations).

        """
        delegate = getattr(self._inner, "close", None)
        if delegate is None:
            return None
        return delegate()


def add_fetch_middleware(middleware: FetchMiddleware) -> None:
    """Append *middleware* to the active fetch middleware registry.

    The call is threaded through the current DI scope. Registrations
    remain visible to subsequent fetch operations (including streaming);
    ordering is ``middlewares[0]`` outermost.

    Args:
        middleware: Callable invoked with the request view and a ``next``
            handle.

    Raises:
        RuntimeError: If no registry is available in the current scope
            (no active render context).

    """
    from webcompy.di import inject
    from webcompy.ports._keys import FETCH_MIDDLEWARE_KEY

    registry = inject(FETCH_MIDDLEWARE_KEY, default=None)  # type: ignore[type-var]
    if registry is None:
        raise RuntimeError("No active fetch middleware registry in the current DI scope")
    registry.use(middleware)  # type: ignore[attr-defined]
