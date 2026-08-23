import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_typed_realtime_page_renders_inside_layout(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/typed-realtime")
    assert page.title() == "Typed Realtime - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="Typed Realtime")).to_be_visible()


@pytest.mark.e2e
def test_typed_realtime_page_toc(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/typed-realtime")
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#typed-messages"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#the-wire-envelope"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#strict-reconstruction"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#error-handling"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#custom-types"]')).to_be_visible()


@pytest.mark.e2e
def test_typed_realtime_page_pager(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/typed-realtime")
    expect(page.locator(".docs-pager-prev")).to_have_count(1)
    expect(page.locator(".docs-pager-prev a")).to_have_text("WebSocket")
    expect(page.locator(".docs-pager-next")).to_have_count(1)
    expect(page.locator(".docs-pager-next a")).to_have_text("RPC Contracts")
