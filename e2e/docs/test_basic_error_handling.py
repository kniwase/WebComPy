import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_basic_error_handling_page(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/basic/error-handling")
    assert page.title() == "Error Handling - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text("Error Handling")
    expect(page.locator(".docs-toc a").first).to_be_visible()
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()
    expect(page.locator(".docs-pager-prev a")).to_have_text("Storage")
    expect(page.locator(".docs-pager-next a")).to_have_text("UI Primitives")
