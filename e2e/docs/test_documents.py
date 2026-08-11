import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_pyscript_init


@pytest.mark.e2e
def test_documents_index_shows_section_cards(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents")
    expect(page.get_by_role("heading", name="Documentation")).to_be_visible()
    expect(page.get_by_role("heading", name="Getting Started")).to_be_visible()
    expect(page.get_by_role("link", name="Open Installation")).to_be_visible()
    expect(page.get_by_role("link", name="Open Signals and Streams")).to_be_visible()


@pytest.mark.e2e
def test_documents_page_content(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents")
    expect(page.get_by_role("heading", name="Getting Started")).to_be_visible()
    expect(page.get_by_role("heading", name="Guides")).to_be_visible()


@pytest.mark.e2e
def test_documents_page_title(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents")
    assert page.title() == "Documents - WebComPy Docs"


@pytest.mark.e2e
def test_documents_reload_no_error(docs_page_on, docs_console_messages, assert_no_console_errors):
    page = docs_page_on("/documents")
    page.reload()
    _wait_for_pyscript_init(page, docs_console_messages)
