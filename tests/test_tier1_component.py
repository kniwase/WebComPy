import asyncio
import sys

import httpx
import pytest

E2E_DIR = __import__("pathlib").Path(__file__).parent.parent / "tests" / "e2e"


@pytest.fixture(autouse=True)
def _add_e2e_path(monkeypatch):
    monkeypatch.setattr(sys, "path", [str(E2E_DIR), *sys.path])


def _client(app):
    from webcompy.testing import create_test_asgi_app

    asgi = create_test_asgi_app(app)

    async def _get(path, base_url="http://test"):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=asgi), base_url=base_url) as c:
            return await c.get(path)

    async def _post(path, base_url="http://test"):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=asgi), base_url=base_url) as c:
            return await c.post(path)

    return _get, _post


def test_function_style_component():
    from my_app.pages.component import FunctionStylePage

    from webcompy.app import WebComPyApp, WebComPyAppConfig
    from webcompy.router import Router

    router = Router({"path": "/component", "component": FunctionStylePage}, mode="history")
    app = WebComPyApp(root_component=FunctionStylePage, router=router, config=WebComPyAppConfig(base_url="/"))
    get, _ = _client(app)
    resp = asyncio.run(get("/component"))
    assert resp.status_code == 200
    assert "function-style-page" in resp.text
    assert "Hello from function component!" in resp.text


def test_class_style_component():
    from my_app.pages.classstyle import ClassStylePage

    from webcompy.app import WebComPyApp, WebComPyAppConfig
    from webcompy.router import Router

    router = Router({"path": "/component/classstyle", "component": ClassStylePage}, mode="history")
    app = WebComPyApp(root_component=ClassStylePage, router=router, config=WebComPyAppConfig(base_url="/"))
    get, _ = _client(app)
    resp = asyncio.run(get("/component/classstyle"))
    assert resp.status_code == 200
    assert "class-style-page" in resp.text
    assert "Hello from class component!" in resp.text
