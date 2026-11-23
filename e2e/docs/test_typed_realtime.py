import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_typed_realtime_page_renders_inside_layout(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/typed-realtime")
    assert page.title() == "Typed Realtime - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="Typed Realtime", level=1)).to_be_visible()


@pytest.mark.e2e
def test_typed_realtime_page_toc(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/typed-realtime")
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#when-to-use"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#setup"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#recipes"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#behavior-notes"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#pitfalls"]')).to_be_visible()


@pytest.mark.e2e
def test_typed_realtime_page_pager_links_to_rpc_contracts(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/typed-realtime")
    expect(page.locator(".docs-pager-prev")).to_have_count(1)
    expect(page.locator(".docs-pager-prev a")).to_have_text("WebSocket")
    expect(page.locator(".docs-pager-next")).to_have_count(1)
    expect(page.locator(".docs-pager-next a")).to_have_text("RPC Contracts")
