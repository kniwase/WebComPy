import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_websocket_page_renders_inside_layout(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/websocket")
    assert page.title() == "WebSocket - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="WebSocket")).to_be_visible()


@pytest.mark.e2e
def test_websocket_page_toc(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/websocket")
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#connection-handle"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#connection-sharing"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#reconnection"]')).to_be_visible()


@pytest.mark.e2e
def test_websocket_page_pager(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/websocket")
    expect(page.locator(".docs-pager-prev")).to_have_count(1)
    expect(page.locator(".docs-pager-prev a")).to_have_text("Server-Sent Events")
    expect(page.locator(".docs-pager-next")).to_have_count(1)
    expect(page.locator(".docs-pager-next a")).to_have_text("Typed Realtime")
