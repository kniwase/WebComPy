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

    return _get


def test_switch_default_state():
    from my_app.pages.switch_test import SwitchPage

    from webcompy.app import WebComPyApp, WebComPyAppConfig
    from webcompy.router import Router

    router = Router({"path": "/switch", "component": SwitchPage}, mode="history")
    app = WebComPyApp(root_component=SwitchPage, router=router, config=WebComPyAppConfig(base_url="/"))
    get = _client(app)
    resp = asyncio.run(get("/switch"))
    assert resp.status_code == 200
    assert "switch-on" in resp.text
    assert "switch-off" not in resp.text
    assert "on" in resp.text


def test_repeat_initial_empty():
    from my_app.pages.repeat import RepeatPage

    from webcompy.app import WebComPyApp, WebComPyAppConfig
    from webcompy.router import Router

    router = Router({"path": "/repeat", "component": RepeatPage}, mode="history")
    app = WebComPyApp(root_component=RepeatPage, router=router, config=WebComPyAppConfig(base_url="/"))
    get = _client(app)
    resp = asyncio.run(get("/repeat"))
    assert resp.status_code == 200
    assert "repeat-page" in resp.text
    assert "<li" not in resp.text


def test_keyed_repeat_initial_empty():
    from my_app.pages.keyed_repeat import KeyedRepeatPage

    from webcompy.app import WebComPyApp, WebComPyAppConfig
    from webcompy.router import Router

    router = Router({"path": "/keyed-repeat", "component": KeyedRepeatPage}, mode="history")
    app = WebComPyApp(root_component=KeyedRepeatPage, router=router, config=WebComPyAppConfig(base_url="/"))
    get = _client(app)
    resp = asyncio.run(get("/keyed-repeat"))
    assert resp.status_code == 200
    assert "keyed-repeat-page" in resp.text
    assert "<li" not in resp.text


def test_dict_repeat_initial_empty():
    from my_app.pages.dict_repeat import DictRepeatPage

    from webcompy.app import WebComPyApp, WebComPyAppConfig
    from webcompy.router import Router

    router = Router({"path": "/dict-repeat", "component": DictRepeatPage}, mode="history")
    app = WebComPyApp(root_component=DictRepeatPage, router=router, config=WebComPyAppConfig(base_url="/"))
    get = _client(app)
    resp = asyncio.run(get("/dict-repeat"))
    assert resp.status_code == 200
    assert "dict-repeat-page" in resp.text
    assert "<li" not in resp.text


def test_nested_repeat_in_switch_initial_list_view():
    from my_app.pages.nested_dynamic import NestedDynamicPage

    from webcompy.app import WebComPyApp, WebComPyAppConfig
    from webcompy.router import Router

    router = Router({"path": "/nested-dynamic", "component": NestedDynamicPage}, mode="history")
    app = WebComPyApp(root_component=NestedDynamicPage, router=router, config=WebComPyAppConfig(base_url="/"))
    get = _client(app)
    resp = asyncio.run(get("/nested-dynamic"))
    assert resp.status_code == 200
    assert "nested-dynamic-page" in resp.text
    assert "list-view" in resp.text
    assert "grid-view" not in resp.text
    assert resp.text.count("list-item") == 3
