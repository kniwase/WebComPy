import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_what_is_page_title(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/what-is-webcompy")
    assert page.title() == "What is WebComPy - WebComPy Docs"


@pytest.mark.e2e
def test_what_is_page_content(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/what-is-webcompy")
    expect(page.locator("article.prose h1#what-is-webcompy")).to_be_visible()
    expect(page.locator(".docs-toc a").first).to_be_visible()


@pytest.mark.e2e
def test_what_is_first_page_omits_prev_link(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/what-is-webcompy")
    expect(page.locator(".docs-pager-prev")).to_have_count(0)
    expect(page.locator(".docs-pager-next")).to_have_count(1)
    expect(page.locator(".docs-pager-next a")).to_have_text("Why WebComPy")
