import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_why_page_title(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/why-webcompy")
    assert page.title() == "Why WebComPy - WebComPy Docs"


@pytest.mark.e2e
def test_why_page_content(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/why-webcompy")
    expect(page.locator("article.prose h1#why-webcompy")).to_be_visible()
    expect(page.locator(".docs-toc a").first).to_be_visible()


@pytest.mark.e2e
def test_why_page_names_trade_offs(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/why-webcompy")
    expect(page.locator("article.prose h2#why-not-webcompy")).to_be_visible()
    expect(page.get_by_text("cold start", exact=False).first).to_be_visible()


@pytest.mark.e2e
def test_why_page_shows_both_links(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/why-webcompy")
    expect(page.locator(".docs-pager-prev a")).to_have_text("What is WebComPy")
    expect(page.locator(".docs-pager-next a")).to_have_text("Installation")
