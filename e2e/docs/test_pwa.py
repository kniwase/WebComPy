import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_pwa_page_renders_inside_layout(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/pwa")
    assert page.title() == "Progressive Web App - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="Progressive Web App")).to_be_visible()


@pytest.mark.e2e
def test_pwa_page_toc(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/pwa")
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#precache"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#runtime-caching"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#offline-fallback"]')).to_be_visible()


@pytest.mark.e2e
def test_pwa_page_is_last_page_no_next_pager(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/pwa")
    expect(page.locator(".docs-pager-prev")).to_have_count(1)
    expect(page.locator(".docs-pager-prev a")).to_have_text("RPC over WebSocket")
    expect(page.locator(".docs-pager-next")).to_have_count(0)
