import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_last_page_omits_next_link(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/signal-stream")
    expect(page.locator(".docs-pager-prev")).to_have_count(1)
    expect(page.locator(".docs-pager-prev a")).to_have_text("Quickstart")
    expect(page.locator(".docs-pager-next")).to_have_count(0)


@pytest.mark.e2e
def test_signal_stream_renders_inside_layout(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/signal-stream")
    assert page.title() == "Signal Stream - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="Signals and Streams")).to_be_visible()
