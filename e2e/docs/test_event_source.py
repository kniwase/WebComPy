import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_event_source_page_renders_inside_layout(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/event-source")
    assert page.title() == "Server-Sent Events - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="Server-Sent Events")).to_be_visible()


@pytest.mark.e2e
def test_event_source_page_toc(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/event-source")
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#basic-usage"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#connection-handle"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#connection-sharing"]')).to_be_visible()


@pytest.mark.e2e
def test_event_source_page_pager_omits_next(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/event-source")
    expect(page.locator(".docs-pager-prev")).to_have_count(1)
    expect(page.locator(".docs-pager-prev a")).to_have_text("Loading Screen")
    expect(page.locator(".docs-pager-next")).to_have_count(0)
