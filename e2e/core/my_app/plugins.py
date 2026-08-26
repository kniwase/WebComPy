from webcompy.app import PluginScript
from webcompy.plugin import WebComPyPlugin


class ErudaPlugin(WebComPyPlugin):
    name = "eruda"

    @staticmethod
    def get_scripts() -> list[PluginScript]:
        return [
            PluginScript(
                attrs={
                    "type": "text/javascript",
                    "src": "https://cdnjs.cloudflare.com/ajax/libs/eruda/2.4.1/eruda.min.js",
                },
                script="eruda.init();",
                in_head=True,
                condition="new URLSearchParams(location.search).get('debug') === 'True'",
            ),
        ]


class MockFetchPlugin(WebComPyPlugin):
    """Intercept a dedicated fetch URL for the mock E2E page."""

    name = "mock-fetch"

    @staticmethod
    def get_fetch_middlewares() -> list[object]:
        """Return a middleware that short-circuits ``GET /api/mock-echo``."""

        async def intercept(request, next):  # type: ignore[no-untyped-def]
            if request.url == "/api/mock-echo":
                from webcompy.ports._fetch import Response

                return Response(
                    text='{"echoed": "mock"}',
                    headers={},
                    status_code=200,
                    status_text="OK",
                    ok=True,
                )
            return await next(request)

        return [intercept]


class MockRpcPlugin(WebComPyPlugin):
    """Mock the ``mock_add`` procedure browser-side without a server route."""

    name = "mock-rpc"

    @staticmethod
    def get_rpc_middlewares() -> list[object]:
        """Return a middleware that synthesizes ``mock_add`` results."""

        async def intercept(ctx, next):  # type: ignore[no-untyped-def]
            if ctx.method == "mock_add":
                return await next(ctx, response={"result": 99})
            return await next(ctx)

        return [intercept]
