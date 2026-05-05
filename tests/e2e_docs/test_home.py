import pytest

from tests.e2e_docs.conftest import _wait_for_pyscript_init


@pytest.mark.e2e
def test_home_page_heading(docs_app_page, assert_no_console_errors):
    heading = docs_app_page.get_by_role("heading", name="What is WebComPy")
    assert heading.is_visible()


@pytest.mark.e2e
def test_home_page_title(docs_app_page, assert_no_console_errors):
    assert docs_app_page.title() == "WebComPy - Python Frontend Framework"


@pytest.mark.e2e
def test_home_spa_navigation_to_helloworld(docs_app_page, assert_no_console_errors):
    dropdown_toggle = docs_app_page.locator("[data-bs-toggle='dropdown']").filter(has_text="Demos")
    dropdown_toggle.click()
    helloworld_link = docs_app_page.get_by_role("link", name="HelloWorld")
    helloworld_link.click()
    assert "/sample/helloworld" in docs_app_page.url
    heading = docs_app_page.get_by_role("heading", name="Hello WebComPy!")
    assert heading.is_visible()


@pytest.mark.e2e
def test_home_spa_navigation_back_from_helloworld(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/helloworld")
    home_link = page.get_by_role("link", name="Home")
    home_link.click()
    assert page.url.endswith("/") or page.url == page.url.rstrip("/") + "/"
    heading = page.get_by_role("heading", name="What is WebComPy")
    assert heading.is_visible()


@pytest.mark.e2e
def test_home_reload_no_error(docs_app_page, docs_console_errors, assert_no_console_errors):
    docs_app_page.reload()
    _wait_for_pyscript_init(docs_app_page, docs_console_errors)
