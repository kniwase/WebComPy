import asyncio
import importlib.util
from pathlib import Path

import pytest

from webcompy.app._app import WebComPyApp
from webcompy.di._scope import DIScope
from webcompy.ports._fetch import Response
from webcompy.ports._keys import FETCH_PORT_KEY
from webcompy_server.ports import VirtualDOMEvent
from webcompy_testing import FakeFetchPort, TestRenderer, mock_app_run

DOCS_APP_DIR = Path(__file__).parent.parent / "docs_app"

_MATPLOTLIB_AVAILABLE = (
    importlib.util.find_spec("matplotlib") is not None and importlib.util.find_spec("numpy") is not None
)
skip_matplotlib = pytest.mark.skipif(not _MATPLOTLIB_AVAILABLE, reason="Requires numpy and matplotlib")


@pytest.fixture(autouse=True)
def _add_docs_app_path(monkeypatch):
    import sys

    monkeypatch.setattr(sys, "path", [str(DOCS_APP_DIR), *sys.path])


def test_mock_app_run_replaces_run_with_noop():
    original = WebComPyApp.run
    with mock_app_run():
        assert WebComPyApp.run is not original
    assert WebComPyApp.run is original


def test_mock_app_run_restores_on_exception():
    original = WebComPyApp.run
    try:
        with mock_app_run():
            raise ValueError("test")
    except ValueError:
        pass
    assert WebComPyApp.run is original


def test_helloworld_renders_heading():
    with mock_app_run():
        from static._demos.helloworld.app import HelloWorld as App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "Hello WebComPy!" in html
            assert "<h1" in html.lower()


def test_helloworld_heading_text():
    with mock_app_run():
        from static._demos.helloworld.app import HelloWorld as App

        with TestRenderer.render(App) as result:
            heading = result.query_selector("h1")
            assert heading is not None
            assert heading.textContent == "Hello WebComPy!"


def test_todo_initial_items():
    with mock_app_run():
        from static._demos.todo.app import TodoApp as App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "Try WebComPy" in html
            assert "Create WebComPy project" in html


def test_todo_add_item():
    with mock_app_run():
        from static._demos.todo.app import TodoApp as App

        with TestRenderer.render(App) as result:
            input_elems = result.query_selector_all("input")
            title_input = input_elems[0] if input_elems else None
            assert title_input is not None
            title_input.value = "Test item"
            add_btn = result.find_by_text("Add ToDo")
            assert add_btn is not None
            add_btn.dispatchEvent(VirtualDOMEvent("click"))
            items = result.query_selector_all("li")
            assert any("Test item" in (item.textContent or "") for item in items)


def test_todo_toggle_checkbox():
    with mock_app_run():
        from static._demos.todo.app import TodoApp as App

        with TestRenderer.render(App) as result:
            checkboxes = [n for n in result.query_selector_all("input") if n.getAttribute("type") == "checkbox"]
            assert len(checkboxes) >= 1
            checkbox = checkboxes[0]
            checkbox.checked = True
            checkbox.dispatchEvent(VirtualDOMEvent("change"))
            span = result.query_selector("span")
            assert span is not None
            assert "line-through" in (span.getAttribute("style") or "")


def test_todo_remove_done_items():
    with mock_app_run():
        from static._demos.todo.app import TodoApp as App

        with TestRenderer.render(App) as result:
            checkboxes = [n for n in result.query_selector_all("input") if n.getAttribute("type") == "checkbox"]
            assert len(checkboxes) >= 1
            checkbox = checkboxes[0]
            checkbox.checked = True
            checkbox.dispatchEvent(VirtualDOMEvent("change"))
            remove_btn = result.find_by_text("Remove Done Items")
            assert remove_btn is not None
            remove_btn.dispatchEvent(VirtualDOMEvent("click"))
            items = result.query_selector_all("li")
            assert not any("Try WebComPy" in (item.textContent or "") for item in items)
            assert any("Create WebComPy project" in (item.textContent or "") for item in items)


def test_teleport_demo_renders_controls():
    with mock_app_run():
        from static._demos.teleport.app import TeleportDemo as App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "Teleport Demo" in html
            assert "Open Modal" in html
            assert "Toggle Dropdown" in html
            assert "Teleported Modal" not in html


def test_transition_demo_renders_controls():
    with mock_app_run():
        from static._demos.transition.app import TransitionDemo as App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "Transition Demo" in html
            assert "Toggle Fade" in html
            assert "Toggle Slide" in html
            assert "Fade content" not in html
            assert "Slide content" not in html


def test_transition_demo_toggle_fade():
    with mock_app_run():
        from static._demos.transition.app import TransitionDemo as App

        with TestRenderer.render(App) as result:
            toggle = result.find_by_text("Toggle Fade")
            assert toggle is not None
            toggle.dispatchEvent(VirtualDOMEvent("click"))
            box = result.find_by_text("Fade content")
            assert box is not None
            assert "fade-enter-from" in (box.getAttribute("class") or "").split()

            result.transition_port.set_style(box, "transition-duration", "400ms")
            result.transition_port.flush_frame()
            classes = (box.getAttribute("class") or "").split()
            assert "fade-enter-from" not in classes
            assert "fade-enter-active" in classes
            assert "fade-enter-to" in classes

            result.transition_port.advance_time(400)
            assert (box.getAttribute("class") or "").split() == ["demo-fade-box"]


@pytest.mark.asyncio
async def test_fetch_page_loads():
    demo_dir = DOCS_APP_DIR / "static" / "_demos" / "fetch_sample"
    responses = {
        ("GET", f"/_demos/fetch_sample/{name}"): Response(
            text=(demo_dir / name).read_text(),
            headers={"content-type": "application/json"},
            status_code=200,
            status_text="OK",
            ok=True,
        )
        for name in ("sample_object.json", "sample_array.json", "sample_scalar.json")
    }
    scope = DIScope()
    scope.provide(FETCH_PORT_KEY, FakeFetchPort(responses=responses))

    with mock_app_run():
        from static._demos.fetch_sample.app import FetchSample as App

        with TestRenderer.render(App, parent_scope=scope) as result:
            # Yield to the event loop so that fire-and-forget async tasks
            # scheduled via resolve_async / _aio_run_server during
            # on_after_rendering have a chance to complete before we
            # assert the rendered output.
            await asyncio.sleep(0)
            html = result.to_html()
            assert "User Data" in html
            assert "Alice" in html
            assert "Bob" in html
            assert "Charlie" in html
            assert "Total users: 3" in html


@skip_matplotlib
def test_matplotlib_page_heading():
    with mock_app_run():
        from static._demos.matplotlib_sample.app import MatplotlibSample as App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "Square Wave" in html


@skip_matplotlib
def test_matplotlib_initial_value():
    with mock_app_run():
        from static._demos.matplotlib_sample.app import MatplotlibSample as App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "Value: 15" in html


@skip_matplotlib
def test_matplotlib_increment_button():
    with mock_app_run():
        from static._demos.matplotlib_sample.app import MatplotlibSample as App

        with TestRenderer.render(App) as result:
            add_btn = result.find_by_text("+")
            assert add_btn is not None
            add_btn.dispatchEvent(VirtualDOMEvent("click"))
            assert "Value: 16" in result.to_html()


@skip_matplotlib
def test_matplotlib_image_rendered():
    with mock_app_run():
        from static._demos.matplotlib_sample.app import MatplotlibSample as App

        with TestRenderer.render(App) as result:
            img = result.query_selector("img")
            assert img is not None
            src = img.getAttribute("src")
            assert src is not None
            assert src.startswith("data:image/png;base64,")


def _make_router_scope(mod_router, path: str = "/") -> tuple[DIScope, object]:
    from tests.conftest import MockHistoryPort
    from webcompy.di._keys import _ROUTER_KEY
    from webcompy.ports._keys import HISTORY_PORT_KEY
    from webcompy.router import Router, RouterKey

    hist = MockHistoryPort()
    hist.navigate(path, None)
    test_router = Router(*mod_router.__pages__, default=mod_router._default, history=hist, preload=False)
    scope = DIScope()
    scope.provide(_ROUTER_KEY, test_router)
    scope.provide(RouterKey, test_router)
    scope.provide(HISTORY_PORT_KEY, hist)
    return scope, hist


def _make_failing_fetch_port():
    from webcompy.ports._fetch import FetchPort

    class _FailingFetchPort(FetchPort):
        async def fetch(
            self,
            url: str,
            *,
            method: str = "GET",
            headers: dict[str, str] | None = None,
            body: str | bytes | None = None,
        ) -> Response:
            raise AssertionError(f"Unexpected network call: {method} {url}")

    return _FailingFetchPort()


def test_todo_tutorial_step1_renders_and_filters():
    with mock_app_run():
        from static._demos.todo_tutorial.step1.app import TodoApp as App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "ToDo Tutorial" in html
            assert "2 remaining" in html
            assert len(result.query_selector_all("li")) == 3

            active_btn = result.find_by_text("Active")
            assert active_btn is not None
            active_btn.dispatchEvent(VirtualDOMEvent("click"))
            items = result.query_selector_all("li")
            assert len(items) == 2
            assert all("Read Getting Started" not in (item.textContent or "") for item in items)

            done_btn = result.find_by_text("Done")
            assert done_btn is not None
            done_btn.dispatchEvent(VirtualDOMEvent("click"))
            done_items = result.query_selector_all("li")
            assert len(done_items) == 1
            assert "Read Getting Started" in (done_items[0].textContent or "")


def test_todo_tutorial_step2_renders_extracted_components():
    with mock_app_run():
        from static._demos.todo_tutorial.step2.app import TodoApp as App

        with TestRenderer.render(App) as result:
            assert result.query_selector("todo-toolbar") is not None
            assert len(result.query_selector_all("todo-item")) == 3
            assert "2 remaining" in result.to_html()


def test_todo_tutorial_step3_navigation():
    with mock_app_run():
        from static._demos.todo_tutorial.step3.app import TodoApp as App
        from static._demos.todo_tutorial.step3.app import router as mod_router

        from tests.conftest import MockHistoryPort

        scope, hist = _make_router_scope(mod_router, "/")
        assert isinstance(hist, MockHistoryPort)
        with TestRenderer.render(App, parent_scope=scope) as result:
            assert len(result.query_selector_all("li")) == 3
            hist.navigate("/active", None)
            active_items = result.query_selector_all("li")
            assert len(active_items) == 2
            assert all("Read Getting Started" not in (item.textContent or "") for item in active_items)
            hist.navigate("/done", None)
            done_items = result.query_selector_all("li")
            assert len(done_items) == 1
            assert "Read Getting Started" in (done_items[0].textContent or "")


@pytest.mark.asyncio
async def test_todo_tutorial_step4_add_task_form():
    from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

    with mock_app_run():
        from static._demos.todo_tutorial.step4.app import TodoApp as App
        from static._demos.todo_tutorial.step4.app import router as mod_router

        scope, _ = _make_router_scope(mod_router, "/")
        with TestRenderer.render(App, parent_scope=scope) as result:
            assert len(result.query_selector_all("li")) == 3
            text_inputs = [n for n in result.query_selector_all("input") if n.getAttribute("type") == "text"]
            assert len(text_inputs) == 1
            text_inputs[0].value = "Write tutorial tests"
            text_inputs[0].dispatchEvent(VirtualDOMEvent("input"))
            form_el = result.query_selector("form")
            assert form_el is not None
            form_el.dispatchEvent(VirtualDOMEvent("submit"))
            await result._scope.inject(ASYNC_SCHEDULER_PORT_KEY).drain()
            items = result.query_selector_all("li")
            assert len(items) == 4
            assert any("Write tutorial tests" in (item.textContent or "") for item in items)


@pytest.mark.asyncio
async def test_todo_tutorial_step5_middleware_direct():
    import json

    from webcompy.ports._middleware import FetchRequest

    with mock_app_run():
        from static._demos.todo_tutorial.step5.app import create_tasks_api

        mw = create_tasks_api()

        async def fail_next(req: FetchRequest, *, response=None):
            raise AssertionError(f"next should not be called for {req.method} {req.url}")

        res_get = await mw(FetchRequest(url="/api/tasks", method="GET", headers=None, body=None), fail_next)
        assert isinstance(res_get, Response)
        assert res_get.status_code == 200
        assert len(json.loads(res_get.text)) == 3

        res_post = await mw(
            FetchRequest(url="/api/tasks", method="POST", headers=None, body=json.dumps({"title": "Ship docs"})),
            fail_next,
        )
        assert isinstance(res_post, Response)
        assert res_post.status_code == 201
        created = json.loads(res_post.text)
        assert created["title"] == "Ship docs"
        assert created["done"] is False

        res_patch = await mw(
            FetchRequest(
                url="/api/tasks/2",
                method="PATCH",
                headers=None,
                body=json.dumps({"done": True}),
            ),
            fail_next,
        )
        assert isinstance(res_patch, Response)
        assert res_patch.status_code == 200
        assert json.loads(res_patch.text)["done"] is True

        passed_urls: list[str] = []

        async def ok_next(req: FetchRequest, *, response=None):
            passed_urls.append(req.url)
            return Response(text="ok", headers={}, status_code=200, status_text="OK", ok=True)

        await mw(FetchRequest(url="/other", method="GET", headers=None, body=None), ok_next)
        assert passed_urls == ["/other"]


@pytest.mark.asyncio
async def test_todo_tutorial_step5_renders_with_middleware():
    from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, FETCH_MIDDLEWARE_KEY
    from webcompy.ports._middleware import FetchMiddlewareRegistry, _MiddlewareFetchPort

    with mock_app_run():
        from static._demos.todo_tutorial.step5.app import TodoApp as App
        from static._demos.todo_tutorial.step5.app import router as mod_router

        scope, _ = _make_router_scope(mod_router, "/")
        registry = FetchMiddlewareRegistry()
        scope.provide(FETCH_MIDDLEWARE_KEY, registry)
        scope.provide(FETCH_PORT_KEY, _MiddlewareFetchPort(_make_failing_fetch_port(), registry))

        with TestRenderer.render(App, parent_scope=scope) as result:
            await result._scope.inject(ASYNC_SCHEDULER_PORT_KEY).drain()
            html = result.to_html()
            assert "Connect to /api/tasks" in html
            assert "2 remaining" in html
            text_inputs = [n for n in result.query_selector_all("input") if n.getAttribute("type") == "text"]
            assert len(text_inputs) == 1
            text_inputs[0].value = "Verify mock submit"
            text_inputs[0].dispatchEvent(VirtualDOMEvent("input"))
            form_el = result.query_selector("form")
            assert form_el is not None
            form_el.dispatchEvent(VirtualDOMEvent("submit"))
            await result._scope.inject(ASYNC_SCHEDULER_PORT_KEY).drain()
            items = result.query_selector_all("li")
            assert len(items) == 4
            assert any("Verify mock submit" in (item.textContent or "") for item in items)


@pytest.mark.asyncio
async def test_todo_tutorial_step6_renders_with_error_boundary():
    from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, FETCH_MIDDLEWARE_KEY
    from webcompy.ports._middleware import FetchMiddlewareRegistry, _MiddlewareFetchPort

    with mock_app_run():
        from static._demos.todo_tutorial.step6.app import TodoApp as App
        from static._demos.todo_tutorial.step6.app import router as mod_router

        scope, _ = _make_router_scope(mod_router, "/")
        registry = FetchMiddlewareRegistry()
        scope.provide(FETCH_MIDDLEWARE_KEY, registry)
        scope.provide(FETCH_PORT_KEY, _MiddlewareFetchPort(_make_failing_fetch_port(), registry))

        with TestRenderer.render(App, parent_scope=scope) as result:
            await result._scope.inject(ASYNC_SCHEDULER_PORT_KEY).drain()
            html = result.to_html()
            assert "Prepare for static deploy" in html
            assert len(result.query_selector_all("li")) == 3


def test_routing_demo_nested_layout_and_guard():
    with mock_app_run():
        from static._demos.routing.app import RoutingDemoApp as App
        from static._demos.routing.app import router as mod_router

        from webcompy.di._keys import _ROUTER_KEY

        scope, _hist = _make_router_scope(mod_router, "/")
        test_router = scope.inject(_ROUTER_KEY)
        test_router.before_route_change = list(mod_router.before_route_change)

        with TestRenderer.render(App, parent_scope=scope) as result:
            assert "Home View" in result.to_html()
            test_router.__set_path__("/workspace", None)
            assert "Workspace Overview" in result.to_html()
            assert "Sidebar: expanded" in result.to_html()
            toggle_btn = result.find_by_text("Toggle Sidebar")
            assert toggle_btn is not None
            toggle_btn.dispatchEvent(VirtualDOMEvent("click"))
            assert "Sidebar: compact" in result.to_html()

            test_router.__set_path__("/workspace/items/42", None)
            html = result.to_html()
            assert "Workspace Item #42" in html
            assert "Sidebar: compact" in html

            test_router.__set_path__("/admin", None)
            html = result.to_html()
            assert "Sign In" in html
            assert "Redirected from /admin" in html

            sign_in_btn = result.find_by_text("Sign in as Admin")
            assert sign_in_btn is not None
            sign_in_btn.dispatchEvent(VirtualDOMEvent("click"))
            assert "Protected Admin" in result.to_html()


def test_storage_sync_demo_state_updates():
    with mock_app_run():
        from static._demos.storage_sync.app import StorageSyncDemo as App

        with TestRenderer.render(App) as result:
            assert "Theme: ocean" in result.to_html()
            assert "Count: 0" in result.to_html()
            forest_btn = result.find_by_text("Forest")
            assert forest_btn is not None
            forest_btn.dispatchEvent(VirtualDOMEvent("click"))
            inc_btn = result.find_by_text("+1 Counter")
            assert inc_btn is not None
            inc_btn.dispatchEvent(VirtualDOMEvent("click"))
            html = result.to_html()
            assert "Theme: forest" in html
            assert "Count: 1" in html


def test_i18n_playground_switches_locale_and_plural():
    with mock_app_run():
        from static._demos.i18n_playground.app import I18nPlaygroundApp as App
        from static._demos.i18n_playground.app import I18nPlaygroundRoot, make_i18n_manager

        from webcompy.i18n import I18N_KEY

        with TestRenderer.render(I18nPlaygroundRoot) as root_result:
            assert "Current locale: en" in root_result.to_html()
            assert "3 items" in root_result.to_html()

        scope = DIScope()
        scope.provide(I18N_KEY, make_i18n_manager())
        with TestRenderer.render(App, parent_scope=scope) as result:
            assert "Current locale: en" in result.to_html()
            assert "3 items" in result.to_html()

            ja_btn = result.find_by_text("日本語")
            assert ja_btn is not None
            ja_btn.dispatchEvent(VirtualDOMEvent("click"))
            assert "現在のロケール: ja" in result.to_html()
            assert "3 個のアイテム" in result.to_html()

            plus_btn = result.find_by_text("+")
            assert plus_btn is not None
            plus_btn.dispatchEvent(VirtualDOMEvent("click"))
            assert "4 個のアイテム" in result.to_html()


@pytest.mark.asyncio
async def test_fetch_middleware_mock_demo_direct_and_rendered():
    import json

    from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, FETCH_MIDDLEWARE_KEY
    from webcompy.ports._middleware import FetchMiddlewareRegistry, FetchRequest, _MiddlewareFetchPort

    with mock_app_run():
        from static._demos.fetch_middleware_mock.app import FetchMiddlewareDemo as App
        from static._demos.fetch_middleware_mock.app import create_notes_mock

        mw = create_notes_mock()

        async def fail_next(req: FetchRequest, *, response=None):
            raise AssertionError(f"next should not be called for {req.method} {req.url}")

        res_get = await mw(FetchRequest(url="/api/notes", method="GET", headers=None, body=None), fail_next)
        assert isinstance(res_get, Response)
        assert len(json.loads(res_get.text)) == 2

        scope = DIScope()
        registry = FetchMiddlewareRegistry()
        scope.provide(FETCH_MIDDLEWARE_KEY, registry)
        scope.provide(FETCH_PORT_KEY, _MiddlewareFetchPort(_make_failing_fetch_port(), registry))

        with TestRenderer.render(App, parent_scope=scope) as result:
            await result._scope.inject(ASYNC_SCHEDULER_PORT_KEY).drain()
            await asyncio.sleep(0)
            html = result.to_html()
            assert "Intercept GET /api/notes" in html
            assert "GET /api/notes -&gt; 200" in html or "GET /api/notes -> 200" in html

            inputs = [n for n in result.query_selector_all("input") if n.getAttribute("type") == "text"]
            assert len(inputs) == 1
            inputs[0].value = "Added mock note"
            inputs[0].dispatchEvent(VirtualDOMEvent("input"))
            add_btn = result.find_by_text("Add Note")
            assert add_btn is not None
            add_btn.dispatchEvent(VirtualDOMEvent("click"))
            await asyncio.sleep(0)
            await result._scope.inject(ASYNC_SCHEDULER_PORT_KEY).drain()
            assert "Added mock note" in result.to_html()


@pytest.mark.asyncio
async def test_rpc_middleware_mock_demo_single_and_batch():
    from webcompy.di._keys import RPC_MIDDLEWARE_KEY, RPC_REGISTRY_KEY
    from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
    from webcompy.rpc._middleware import RpcMiddlewareRegistry
    from webcompy.rpc._registry import ProcedureRegistry

    with mock_app_run():
        from static._demos.rpc_middleware_mock.app import RpcMiddlewareDemo as App

        scope = DIScope()
        scope.provide(RPC_REGISTRY_KEY, ProcedureRegistry())
        scope.provide(RPC_MIDDLEWARE_KEY, RpcMiddlewareRegistry())
        scope.provide(FETCH_PORT_KEY, _make_failing_fetch_port())

        with TestRenderer.render(App, parent_scope=scope) as result:
            monitor_btn = result.find_by_text("Monitor")
            assert monitor_btn is not None
            monitor_btn.dispatchEvent(VirtualDOMEvent("click"))
            plus_btn = result.find_by_text("+")
            assert plus_btn is not None
            plus_btn.dispatchEvent(VirtualDOMEvent("click"))

            quote_btn = result.find_by_text("Request Quote")
            assert quote_btn is not None
            quote_btn.dispatchEvent(VirtualDOMEvent("click"))
            await asyncio.sleep(0)
            await result._scope.inject(ASYNC_SCHEDULER_PORT_KEY).drain()
            assert "3x Monitor @ $340" in result.to_html()
            assert "Total: $1020" in result.to_html()

            batch_btn = result.find_by_text("Run Batch")
            assert batch_btn is not None
            batch_btn.dispatchEvent(VirtualDOMEvent("click"))
            await asyncio.sleep(0)
            await result._scope.inject(ASYNC_SCHEDULER_PORT_KEY).drain()
            assert "Catalog size: 3 items (USD)" in result.to_html()
