import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_basic_markdown_documents_page(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/basic/markdown-documents")
    assert page.title() == "Markdown Documents - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text("Markdown Documents")
    expect(page.locator(".docs-toc a").first).to_be_visible()
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()
