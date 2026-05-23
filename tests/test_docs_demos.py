from pathlib import Path

import pytest

from webcompy.app._app import WebComPyApp
from webcompy.ports._server._virtual_dom import VirtualDOMEvent
from webcompy.testing import TestRenderer, mock_app_run

DOCS_APP_DIR = Path(__file__).parent.parent / "docs_app"


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
        from static._demos.helloworld.app import App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "Hello WebComPy!" in html
            assert "<h1" in html.lower()


def test_helloworld_heading_text():
    with mock_app_run():
        from static._demos.helloworld.app import App

        with TestRenderer.render(App) as result:
            heading = result.query_selector("h1")
            assert heading is not None
            assert heading.textContent == "Hello WebComPy!"


def test_fizzbuzz_initial_state():
    with mock_app_run():
        from static._demos.fizzbuzz.app import App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "Count: 10" in html


def test_fizzbuzz_add_button():
    with mock_app_run():
        from static._demos.fizzbuzz.app import App

        with TestRenderer.render(App) as result:
            add_btn = result.find_by_text("Add")
            assert add_btn is not None
            add_btn.dispatchEvent(VirtualDOMEvent("click"))
            assert "Count: 11" in result.to_html()


def test_fizzbuzz_pop_button():
    with mock_app_run():
        from static._demos.fizzbuzz.app import App

        with TestRenderer.render(App) as result:
            pop_btn = result.find_by_text("Pop")
            assert pop_btn is not None
            pop_btn.dispatchEvent(VirtualDOMEvent("click"))
            assert "Count: 9" in result.to_html()


def test_fizzbuzz_hide_toggle():
    with mock_app_run():
        from static._demos.fizzbuzz.app import App

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
        from static._demos.todo.app import App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "Try WebComPy" in html
            assert "Create WebComPy project" in html


def test_todo_add_item():
    with mock_app_run():
        from static._demos.todo.app import App

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
        from static._demos.todo.app import App

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
        from static._demos.todo.app import App

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


def test_fetch_page_loads():
    with mock_app_run():
        from static._demos.fetch_sample.app import App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "User Data" in html
            assert "Alice" in html
            assert "Bob" in html
            assert "Charlie" in html


def test_matplotlib_page_heading():
    with mock_app_run():
        from static._demos.matplotlib_sample.app import App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "Square Wave" in html


def test_matplotlib_initial_value():
    with mock_app_run():
        from static._demos.matplotlib_sample.app import App

        with TestRenderer.render(App) as result:
            html = result.to_html()
            assert "Value: 15" in html


def test_matplotlib_increment_button():
    with mock_app_run():
        from static._demos.matplotlib_sample.app import App

        with TestRenderer.render(App) as result:
            add_btn = result.find_by_text("+")
            assert add_btn is not None
            add_btn.dispatchEvent(VirtualDOMEvent("click"))
            assert "Value: 16" in result.to_html()


def test_matplotlib_image_rendered():
    with mock_app_run():
        from static._demos.matplotlib_sample.app import App

        with TestRenderer.render(App) as result:
            img = result.query_selector("img")
            assert img is not None
            src = img.getAttribute("src")
            assert src is not None
            assert src.startswith("data:image/png;base64,")
