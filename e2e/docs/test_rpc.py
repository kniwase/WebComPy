import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_rpc_page_renders_inside_layout(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/rpc")
    assert page.title() == "RPC - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="RPC", exact=True)).to_be_visible()


@pytest.mark.e2e
def test_rpc_page_toc(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/rpc")
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#typed-calls"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#streaming"]')).to_be_visible()


@pytest.mark.e2e
def test_rpc_page_pager(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/rpc")
    expect(page.locator(".docs-pager-prev a")).to_have_text("RPC Contracts")
    expect(page.locator(".docs-pager-next a")).to_have_text("RPC over WebSocket")
