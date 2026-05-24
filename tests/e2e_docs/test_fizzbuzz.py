import pytest

from tests.e2e_docs.conftest import _wait_for_pyscript_init


@pytest.mark.e2e
def test_fizzbuzz_reload_no_error(docs_page_on, docs_console_messages, assert_no_console_errors):
    page = docs_page_on("/sample/fizzbuzz")
    page.reload()
    _wait_for_pyscript_init(page, docs_console_messages)
