"""Fetch middleware validated under the real PyScript runtime.

Top-level imports must stay CPython-importable: browser-only modules are
imported inside function bodies (CPython-importability invariant).
"""

from webcompy.di import inject
from webcompy.ports._fetch import Response
from webcompy.ports._keys import FETCH_MIDDLEWARE_KEY, FETCH_PORT_KEY
from webcompy.ports._middleware import (
    FetchMiddlewareRegistry,
    FetchRequest,
    _MiddlewareFetchPort,
)


def _synthetic() -> Response:
    return Response(text="{}", headers={}, status_code=200, status_text="OK", ok=True)


def test_assembly_installs_middleware_wrapper(app):
    port = inject(FETCH_PORT_KEY)

    assert isinstance(port, _MiddlewareFetchPort)


def test_registry_resolves_per_context(app):
    registry = inject(FETCH_MIDDLEWARE_KEY)

    assert isinstance(registry, FetchMiddlewareRegistry)


async def test_interceptor_short_circuits_without_network(app):
    registry = inject(FETCH_MIDDLEWARE_KEY)

    async def interceptor(request: FetchRequest, next):  # type: ignore[name-defined]
        if request.url == "/mocked":
            return _synthetic()
        return await next(request)

    registry.use(interceptor)
    port = inject(FETCH_PORT_KEY)

    response = await port.fetch("/mocked")

    assert response.ok
    assert response.text == "{}"


async def test_generation_rebuild_replaces_cached_chain(app):
    """A registration bumps the generation and swaps the cached sub-chains."""
    registry = inject(FETCH_MIDDLEWARE_KEY)
    port = inject(FETCH_PORT_KEY)
    port._ensure_chains()
    fetch_head_before = port._fetch_head

    async def extra(request: FetchRequest, next):  # type: ignore[name-defined]
        return await next(request)

    registry.use(extra)
    port._ensure_chains()

    assert port._fetch_head is not fetch_head_before


def test_noop_delegates_to_browser_port(app):
    port = inject(FETCH_PORT_KEY)

    assert port.noop is False
