import pytest

from tests.e2e_docs.conftest import _wait_for_demo_iframe, _wait_for_pyscript_init


@pytest.mark.e2e
def test_fetch_page_loads(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/fetch")
    frame = _wait_for_demo_iframe(page, "fetch_sample")
    heading = frame.get_by_role("heading", name="User Data")
    assert heading.is_visible()


@pytest.mark.e2e
def test_fetch_reload_no_error(docs_page_on, docs_console_messages, assert_no_console_errors):
    page = docs_page_on("/sample/fetch")
    page.reload()
    _wait_for_pyscript_init(page, docs_console_messages)
