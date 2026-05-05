import pytest

from tests.e2e_docs.conftest import _wait_for_pyscript_init


@pytest.mark.e2e
def test_documents_page_content(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents")
    assert page.get_by_text("Work In Progress").is_visible()


@pytest.mark.e2e
def test_documents_page_title(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents")
    assert page.title() == "Documents - WebCompy"


@pytest.mark.e2e
def test_documents_reload_no_error(docs_page_on, docs_console_errors, assert_no_console_errors):
    page = docs_page_on("/documents")
    page.reload()
    _wait_for_pyscript_init(page, docs_console_errors)
