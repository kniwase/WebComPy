import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_pwa_page_renders_inside_layout(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/pwa")
    assert page.title() == "Progressive Web App - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="Progressive Web App", level=1)).to_be_visible()
    expect(page.get_by_role("heading", name="What gets generated", level=2)).to_be_visible()
    expect(page.get_by_role("heading", name="What runs in the browser", level=2)).to_be_visible()
    caching_table = page.locator("article.prose table")
    expect(caching_table).to_be_visible()
    expect(caching_table).to_contain_text("cache-first")
    expect(caching_table).to_contain_text("network-first")
    expect(caching_table).to_contain_text("stale-while-revalidate")


@pytest.mark.e2e
def test_pwa_page_toc(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/pwa")
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#what-gets-generated"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#precache"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#what-runs-in-the-browser"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#runtime-caching"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#offline-fallback"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#next-steps"]')).to_be_visible()


@pytest.mark.e2e
def test_pwa_page_pager(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/pwa")
    expect(page.locator(".docs-pager-prev")).to_have_count(1)
    expect(page.locator(".docs-pager-prev a")).to_have_text("Styling Deep Dive")
    expect(page.locator(".docs-pager-next")).to_have_count(1)
    expect(page.locator(".docs-pager-next a")).to_have_text("Dependency Injection Deep Dive")
