import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe, _wait_for_pyscript_init

pytestmark = pytest.mark.e2e


def test_examples_matplotlib_page_heading(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/matplotlib")
    assert page.title() == "Matplotlib - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text("Matplotlib")
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()

    frame = _wait_for_demo_iframe(page, "matplotlib_sample")
    heading = frame.get_by_role("heading", name="Square Wave")
    assert heading.is_visible()


def test_examples_matplotlib_initial_value(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/matplotlib")
    frame = _wait_for_demo_iframe(page, "matplotlib_sample")
    assert frame.get_by_text("Value: 15").is_visible()


def test_examples_matplotlib_increment_button(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/matplotlib")
    frame = _wait_for_demo_iframe(page, "matplotlib_sample")
    plus_button = frame.get_by_role("button", name="+")
    plus_button.click()
    assert frame.get_by_text("Value: 16").is_visible()


def test_examples_matplotlib_image_rendered(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/matplotlib")
    frame = _wait_for_demo_iframe(page, "matplotlib_sample")
    img = frame.locator("img")
    assert img.is_visible()


def test_examples_matplotlib_reload_no_error(docs_page_on, docs_console_messages, assert_no_console_errors):
    page = docs_page_on("/documents/examples/matplotlib")
    page.reload()
    _wait_for_pyscript_init(page, docs_console_messages)
