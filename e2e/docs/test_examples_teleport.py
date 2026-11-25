import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe

pytestmark = pytest.mark.e2e


def test_examples_teleport_page_loads(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/teleport")
    assert page.title() == "Teleport - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text("Teleport")
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()


def test_examples_teleport_demo_modal_under_body(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/teleport")
    frame = _wait_for_demo_iframe(page, "teleport")
    frame.locator("#open-modal").click()
    modal = frame.locator(".demo-modal")
    expect(modal).to_be_visible()
    assert frame.evaluate("document.querySelector('.demo-modal-backdrop').parentElement.tagName") == "BODY"
    frame.locator("#close-modal").click()
    expect(modal).to_have_count(0)


def test_examples_teleport_demo_dropdown(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/teleport")
    frame = _wait_for_demo_iframe(page, "teleport")
    frame.locator("#toggle-dropdown").click()
    dropdown = frame.locator(".demo-dropdown")
    expect(dropdown).to_be_visible()
    assert frame.evaluate("document.querySelector('.demo-dropdown').parentElement.tagName") == "BODY"
