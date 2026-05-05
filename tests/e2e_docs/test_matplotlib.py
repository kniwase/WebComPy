import pytest

from tests.e2e_docs.conftest import _wait_for_pyscript_init


@pytest.mark.e2e
def test_matplotlib_page_heading(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/matplotlib")
    heading = page.get_by_role("heading", name="Square Wave")
    assert heading.is_visible()


@pytest.mark.e2e
def test_matplotlib_initial_value(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/matplotlib")
    assert page.get_by_text("Value: 15").is_visible()


@pytest.mark.e2e
def test_matplotlib_increment_button(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/matplotlib")
    plus_button = page.get_by_role("button", name="+")
    plus_button.click()
    assert page.get_by_text("Value: 16").is_visible()


@pytest.mark.e2e
def test_matplotlib_image_rendered(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/matplotlib")
    img = page.locator("img")
    assert img.is_visible()


@pytest.mark.e2e
def test_matplotlib_reload_no_error(docs_page_on, docs_console_errors, assert_no_console_errors):
    page = docs_page_on("/sample/matplotlib")
    page.reload()
    _wait_for_pyscript_init(page, docs_console_errors)
