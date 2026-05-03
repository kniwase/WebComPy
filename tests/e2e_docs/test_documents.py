import pytest


@pytest.mark.e2e
def test_documents_page_content(docs_page_on, assert_no_python_errors):
    page = docs_page_on("/documents")
    assert page.get_by_text("Work In Progress").is_visible()


@pytest.mark.e2e
def test_documents_page_title(docs_page_on, assert_no_python_errors):
    page = docs_page_on("/documents")
    assert page.title() == "Documents - WebCompy"
