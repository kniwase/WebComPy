import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_disclosure_page_renders_inside_layout(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/disclosure")
    assert page.title() == "Disclosure & Feedback - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="Disclosure & Feedback")).to_be_visible()


@pytest.mark.e2e
def test_disclosure_page_pager(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/disclosure")
    expect(page.locator(".docs-pager-prev")).to_have_count(1)
    expect(page.locator(".docs-pager-prev a")).to_have_text("Overlay Components")
    expect(page.locator(".docs-pager-next")).to_have_count(1)
    expect(page.locator(".docs-pager-next a")).to_have_text("Loading Screen")


@pytest.mark.e2e
def test_disclosure_page_showcase_renders_tabs(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/disclosure")
    tablist = page.locator(".disclosure-demo [role='tablist']").first
    expect(tablist).to_be_visible()
    expect(tablist.locator("[role='tab']")).to_have_count(3)
    expect(tablist.locator("[role='tab']").first).to_have_attribute("aria-selected", "true")
