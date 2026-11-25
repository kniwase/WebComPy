import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe, _wait_for_pyscript_init

pytestmark = pytest.mark.e2e


def test_examples_http_fetch_page_loads(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/http-fetch")
    assert page.title() == "HTTP Fetch - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text("HTTP Fetch")
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()

    frame = _wait_for_demo_iframe(page, "fetch_sample")
    expect(frame.get_by_role("heading", name="User Data")).to_be_visible()
    expect(frame.get_by_text("Total users: 3")).to_be_visible()


def test_examples_http_fetch_reload_no_error(docs_page_on, docs_console_messages, assert_no_console_errors):
    page = docs_page_on("/documents/examples/http-fetch")
    page.reload()
    _wait_for_pyscript_init(page, docs_console_messages)
