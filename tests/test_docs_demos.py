import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

from tests.conftest import MockHistoryPort
from webcompy.app._app import WebComPyApp
from webcompy.di._keys import _ROUTER_KEY
from webcompy.di._scope import DIScope
from webcompy.ports._fetch import FetchPort, Response
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, FETCH_MIDDLEWARE_KEY, FETCH_PORT_KEY, HISTORY_PORT_KEY
from webcompy.ports._middleware import FetchMiddlewareRegistry, FetchRequest, _MiddlewareFetchPort
from webcompy.router import Router
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


def test_fizzbuzz_initial_state():
    with mock_app_run():
        from static._demos.fizzbuzz.app import FizzbuzzApp as App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "Count: 10" in html


def test_fizzbuzz_add_button():
    with mock_app_run():
        from static._demos.fizzbuzz.app import FizzbuzzApp as App

        with TestRenderer.render(App) as result:
            add_btn = result.find_by_text("Add")
            assert add_btn is not None
            add_btn.dispatchEvent(VirtualDOMEvent("click"))
            assert "Count: 11" in result.to_html()


def test_fizzbuzz_pop_button():
    with mock_app_run():
        from static._demos.fizzbuzz.app import FizzbuzzApp as App

        with TestRenderer.render(App) as result:
            pop_btn = result.find_by_text("Pop")
            assert pop_btn is not None
            pop_btn.dispatchEvent(VirtualDOMEvent("click"))
            assert "Count: 9" in result.to_html()


def test_fizzbuzz_hide_toggle():
    with mock_app_run():
        from static._demos.fizzbuzz.app import FizzbuzzApp as App

        with TestRenderer.render(App) as result:
            assert "FizzBuzz Hidden" not in result.to_html()

            toggle_btn = result.find_by_text("Hide")
            assert toggle_btn is not None
            toggle_btn.dispatchEvent(VirtualDOMEvent("click"))
            assert "FizzBuzz Hidden" in result.to_html()

            open_btn = result.find_by_text("Open")
            assert open_btn is not None
            open_btn.dispatchEvent(VirtualDOMEvent("click"))
            assert "FizzBuzz Hidden" not in result.to_html()


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


def _make_router_scope(mod_router: Router, path: str = "/") -> tuple[DIScope, MockHistoryPort]:
    hist = MockHistoryPort()
    hist.navigate(path, None)
    test_router = Router(*mod_router.__pages__, default=mod_router._default, history=hist, preload=False)
    scope = DIScope()
    scope.provide(_ROUTER_KEY, test_router)
    scope.provide(HISTORY_PORT_KEY, hist)
    return scope, hist


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

        scope, hist = _make_router_scope(mod_router, "/")
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
    with mock_app_run():
        from static._demos.todo_tutorial.step5.app import TodoApp as App
        from static._demos.todo_tutorial.step5.app import router as mod_router

        scope, _ = _make_router_scope(mod_router, "/")
        registry = FetchMiddlewareRegistry()
        scope.provide(FETCH_MIDDLEWARE_KEY, registry)
        scope.provide(FETCH_PORT_KEY, _MiddlewareFetchPort(_FailingFetchPort(), registry))

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
    with mock_app_run():
        from static._demos.todo_tutorial.step6.app import TodoApp as App
        from static._demos.todo_tutorial.step6.app import router as mod_router

        scope, _ = _make_router_scope(mod_router, "/")
        registry = FetchMiddlewareRegistry()
        scope.provide(FETCH_MIDDLEWARE_KEY, registry)
        scope.provide(FETCH_PORT_KEY, _MiddlewareFetchPort(_FailingFetchPort(), registry))

        with TestRenderer.render(App, parent_scope=scope) as result:
            await asyncio.sleep(0)
            html = result.to_html()
            assert "Prepare for static deploy" in html
            assert len(result.query_selector_all("li")) == 3
