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

        result = TestRenderer.render(App)
        html = result.to_html()
        assert "Hello WebComPy!" in html
        assert "<h1" in html.lower()
        result.close()


def test_helloworld_heading_text():
    with mock_app_run():
        from static._demos.helloworld.app import App

        result = TestRenderer.render(App)
        heading = result.query_selector("h1")
        assert heading is not None
        assert heading.textContent == "Hello WebComPy!"
        result.close()


def test_fizzbuzz_initial_state():
    with mock_app_run():
        from static._demos.fizzbuzz.app import App

        result = TestRenderer.render(App)
        html = result.to_html()
        assert "Count: 10" in html
        result.close()


def test_fizzbuzz_add_button():
    with mock_app_run():
        from static._demos.fizzbuzz.app import App

        result = TestRenderer.render(App)
        add_btn = result.find_by_text("Add")
        assert add_btn is not None
        add_btn.dispatchEvent(VirtualDOMEvent("click"))
        assert "Count: 11" in result.to_html()
        result.close()


def test_fizzbuzz_pop_button():
    with mock_app_run():
        from static._demos.fizzbuzz.app import App

        result = TestRenderer.render(App)
        pop_btn = result.find_by_text("Pop")
        assert pop_btn is not None
        pop_btn.dispatchEvent(VirtualDOMEvent("click"))
        assert "Count: 9" in result.to_html()
        result.close()


def test_fizzbuzz_hide_toggle():
    with mock_app_run():
        from static._demos.fizzbuzz.app import App

        result = TestRenderer.render(App)
        assert "FizzBuzz Hidden" not in result.to_html()

        toggle_btn = result.find_by_text("Hide")
        assert toggle_btn is not None
        toggle_btn.dispatchEvent(VirtualDOMEvent("click"))
        assert "FizzBuzz Hidden" in result.to_html()

        open_btn = result.find_by_text("Open")
        assert open_btn is not None
        open_btn.dispatchEvent(VirtualDOMEvent("click"))
        assert "FizzBuzz Hidden" not in result.to_html()
        result.close()
