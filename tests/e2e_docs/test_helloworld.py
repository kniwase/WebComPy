import pytest

from tests.e2e_docs.conftest import _wait_for_pyscript_init


@pytest.mark.e2e
def test_helloworld_page_heading(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/helloworld")
    heading = page.get_by_role("heading", name="Hello WebComPy!")
    assert heading.is_visible()


@pytest.mark.e2e
def test_helloworld_page_text(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/helloworld")
    assert page.locator("h1").get_by_text("Hello WebComPy!").is_visible()


@pytest.mark.e2e
def test_helloworld_reload_no_error(docs_page_on, docs_console_errors, assert_no_console_errors):
    page = docs_page_on("/sample/helloworld")
    page.reload()
    _wait_for_pyscript_init(page, docs_console_errors)
