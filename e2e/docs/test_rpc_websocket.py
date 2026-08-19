import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_rpc_websocket_page_renders_inside_layout(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/rpc-websocket")
    assert page.title() == "RPC over WebSocket - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="RPC over WebSocket")).to_be_visible()


@pytest.mark.e2e
def test_rpc_websocket_page_toc(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/rpc-websocket")
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#typed-calls"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#subscriptions"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#reconnect-catch-up-and-resync"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#heartbeat"]')).to_be_visible()


@pytest.mark.e2e
def test_rpc_websocket_page_is_last_page_no_next_pager(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/rpc-websocket")
    expect(page.locator(".docs-pager-prev")).to_have_count(1)
    expect(page.locator(".docs-pager-prev a")).to_have_text("RPC")
    expect(page.locator(".docs-pager-next")).to_have_count(0)
