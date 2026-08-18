from __future__ import annotations

import html as html_module
import json
from dataclasses import dataclass

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from webcompy.ajax import HttpClient
from webcompy.components._generator import define_component
from webcompy.di import inject
from webcompy.elements import html
from webcompy.hydration._collect import collect_transfer_data
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
from webcompy_server import generate_html
from webcompy_testing import create_test_app
from webcompy_testing._utils import run_sync


@dataclass
class User:
    id: int
    name: str


@define_component("typed-fetch-root")
def TypedFetchRoot(context):
    from webcompy.components._hooks import use_async_result

    result = use_async_result(lambda: HttpClient.get("/api/user", response_type=User))
    return html.DIV({"data-testid": "typed-root"}, result.data.value.name if result.data.value else "")


@define_component("no-transfer-root")
def NoTransferRoot(context):
    from webcompy.components._hooks import use_async_result

    result = use_async_result(
        lambda: HttpClient.get("/api/secret", response_type=User),
        transfer=False,
    )
    return html.DIV({"data-testid": "notransfer-root"}, result.data.value.name if result.data.value else "")


def _render_with_api(root, *, api_path="/api/user", payload=None):
    async def handler(request):
        return JSONResponse(payload if payload is not None else {"id": 1, "name": "ada"})

    app = create_test_app(root_component=root)
    asgi = Starlette(routes=[Route(api_path, endpoint=handler)])
    fetch_port = app._server_fetch_port
    fetch_port.configure(asgi, blocked_paths=[])
    html_str, collected, ctx_port = _render(app)
    return app, ctx_port, (html_str, collected)


def _render(app):
    from webcompy.ports._keys import FETCH_PORT_KEY

    async def _go():
        ctx = app.create_render_context("/")
        try:
            ctx_port = ctx.di_scope.inject(FETCH_PORT_KEY)
            scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
            await scheduler.await_pending()
            html_str = await generate_html(
                ctx,
                app_package_name="test_pkg",
                dev_mode=False,
                prerender=True,
                wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            )
            collected = collect_transfer_data(ctx._root)
            return html_str, collected, ctx_port
        finally:
            ctx.dispose()

    return run_sync(_go())


def _extract_payload(html_str: str) -> dict:
    marker = 'id="__webcompy_data__">'
    start = html_str.index(marker) + len(marker)
    end = html_str.index("</script>", start)
    return json.loads(html_module.unescape(html_str[start:end]))


class TestTypedFetchDuringSsr:
    def test_typed_self_site_fetch_uses_asgi_transport_and_populates_cache(self):
        _app, fetch_port, (html_str, _collected) = _render_with_api(TypedFetchRoot)

        assert "typed-root" in html_str

        assert "/api/user" in fetch_port._response_cache
        cached = fetch_port._response_cache["/api/user"]
        assert cached.status_code == 200
        assert cached.json() == {"id": 1, "name": "ada"}

        payload = _extract_payload(html_str)
        assert payload["async_results"], "expected a transferred async-result entry"

    def test_transfer_false_absent_from_hydration_payload(self):
        _app, fetch_port, (html_str, _collected) = _render_with_api(
            NoTransferRoot,
            api_path="/api/secret",
            payload={"id": 9, "name": "secret-ada"},
        )

        assert "notransfer-root" in html_str

        assert "/api/secret" in fetch_port._response_cache

        payload = _extract_payload(html_str)
        assert payload["async_results"] == {}

    def test_collect_transfer_data_after_typed_render(self):
        _app, fetch_port, (_html_str, collected) = _render_with_api(TypedFetchRoot)
        assert collected.async_results, "expected a collected async-result entry"
        assert "/api/user" in collected.fetches or "/api/user" in fetch_port._response_cache
