import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_project_structure_page_title(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/project-structure")
    assert page.title() == "Project Structure - WebComPy Docs"


@pytest.mark.e2e
def test_project_structure_page_content(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/project-structure")
    expect(page.locator("article.prose h1#project-structure")).to_be_visible()
    expect(page.locator(".docs-toc a").first).to_be_visible()


@pytest.mark.e2e
def test_project_structure_page_pager(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/project-structure")
    expect(page.locator(".docs-pager-prev a")).to_have_text("Quickstart")
    expect(page.locator(".docs-pager-next a")).to_have_text("UI Primitives")
