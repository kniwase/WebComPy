import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe


@pytest.mark.e2e
def test_teleport_page_loads(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/teleport")
    expect(page.locator("h1.page-title")).to_have_text("Teleport")


@pytest.mark.e2e
def test_teleport_demo_modal_under_body(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/teleport")
    frame = _wait_for_demo_iframe(page, "teleport")
    frame.locator("#open-modal").click()
    modal = frame.locator(".demo-modal")
    expect(modal).to_be_visible()
    assert frame.evaluate("document.querySelector('.demo-modal-backdrop').parentElement.tagName") == "BODY"
    frame.locator("#close-modal").click()
    expect(modal).to_have_count(0)


@pytest.mark.e2e
def test_teleport_demo_dropdown(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/teleport")
    frame = _wait_for_demo_iframe(page, "teleport")
    frame.locator("#toggle-dropdown").click()
    dropdown = frame.locator(".demo-dropdown")
    expect(dropdown).to_be_visible()
    assert frame.evaluate("document.querySelector('.demo-dropdown').parentElement.tagName") == "BODY"
