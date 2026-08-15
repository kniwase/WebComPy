from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from starlette.applications import Starlette
from starlette.routing import Mount

from webcompy.aio import AsyncWrapper
from webcompy.ajax import HttpClient
from webcompy.components import ComponentContext, define_component
from webcompy.di._scope import DIScope
from webcompy.elements import html
from webcompy.ports._fetch import Response as PortResponse
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy.signal import use_state
from webcompy_server.contrib.fastapi import TypedJSONResponse
from webcompy_server.ports._fetch import ServerFetchPort
from webcompy_testing import FakeFetchPort, TestRenderer


@dataclass
class TypedRecord:
    name: str
    blob: bytes
    tags: set[str]
    price: Decimal
    at: datetime


def _record() -> TypedRecord:
    return TypedRecord(
        name="alice",
        blob=b"img",
        tags={"a", "b"},
        price=Decimal("12.34"),
        at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    )


def _fastapi_app() -> FastAPI:
    app = FastAPI()

    @app.get("/records/{record_id}")
    def get_record(record_id: int) -> TypedJSONResponse:
        assert record_id == 1
        return TypedJSONResponse(_record())

    return app


@define_component("record-page")
def RecordPage(context: ComponentContext[None]):
    name_text = use_state(lambda: "")
    blob_text = use_state(lambda: "")
    tags_text = use_state(lambda: "")
    price_text = use_state(lambda: "")
    error_text = use_state(lambda: "")

    @AsyncWrapper()
    async def fetch_record():
        try:
            record = await HttpClient.get("/api/records/1", response_type=TypedRecord)
            name_text.value = record.name
            blob_text.value = record.blob.decode("utf-8")
            tags_text.value = ",".join(sorted(record.tags))
            price_text.value = str(record.price)
        except Exception as err:
            error_text.value = f"error: {err}"

    @context.on_after_rendering
    def _():
        fetch_record()

    return html.DIV(
        {},
        html.P({}, name_text),
        html.P({}, blob_text),
        html.P({}, tags_text),
        html.P({}, price_text),
        html.P({}, error_text),
    )


async def _render_and_wait(scope):
    with TestRenderer.render(RecordPage, parent_scope=scope) as result:
        for _ in range(100):
            await asyncio.sleep(0)
            if "alice" in result.to_html():
                break
        return result.to_html()


@pytest.mark.asyncio
async def test_ssr_path_mounted_fastapi_endpoint():
    port = ServerFetchPort()
    app = Starlette(routes=[Mount("/api", app=_fastapi_app())])
    port.configure(app, blocked_paths=["/"], mount_prefixes=["/api"])

    scope = DIScope()
    scope.provide(FETCH_PORT_KEY, port)

    html_output = await _render_and_wait(scope)
    assert "alice" in html_output
    assert "img" in html_output
    assert "a,b" in html_output
    assert "12.34" in html_output
    assert "error" not in html_output


@pytest.mark.asyncio
async def test_browser_path_canned_header_mode_response():
    typed_response = TypedJSONResponse(_record())
    port_response = PortResponse(
        text=typed_response.body.decode("utf-8"),
        headers=dict(typed_response.headers),
        status_code=200,
        status_text="OK",
        ok=True,
    )
    scope = DIScope()
    scope.provide(FETCH_PORT_KEY, FakeFetchPort(responses={("GET", "/api/records/1"): port_response}))

    html_output = await _render_and_wait(scope)
    assert "alice" in html_output
    assert "img" in html_output
    assert "a,b" in html_output
    assert "12.34" in html_output
    assert "error" not in html_output
