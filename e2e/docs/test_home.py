import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe, _wait_for_pyscript_init


@pytest.mark.e2e
def test_home_page_heading(docs_app_page, assert_no_console_errors):
    heading = docs_app_page.get_by_role("heading", name="What is WebComPy")
    expect(heading).to_be_visible()


@pytest.mark.e2e
def test_home_page_title(docs_app_page, assert_no_console_errors):
    assert docs_app_page.title() == "WebComPy - Python Frontend Framework"


@pytest.mark.e2e
def test_home_spa_navigation_to_helloworld(docs_app_page, assert_no_console_errors):
    dropdown_toggle = docs_app_page.locator("nav li a[aria-haspopup='true']").filter(has_text="Demos")
    dropdown_toggle.click()
    helloworld_link = docs_app_page.get_by_role("link", name="HelloWorld")
    helloworld_link.click()
    assert "/sample/helloworld" in docs_app_page.url
    frame = _wait_for_demo_iframe(docs_app_page, "helloworld")
    heading = frame.get_by_role("heading", name="Hello WebComPy!")
    expect(heading).to_be_visible()


@pytest.mark.e2e
def test_home_spa_navigation_back_from_helloworld(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/helloworld")
    home_link = page.locator("nav a[href='/']")
    home_link.click()
    assert page.url.endswith("/") or page.url == page.url.rstrip("/") + "/"
    heading = page.get_by_role("heading", name="What is WebComPy")
    expect(heading).to_be_visible()


@pytest.mark.e2e
def test_home_reload_no_error(docs_app_page, docs_console_messages, assert_no_console_errors):
    docs_app_page.reload()
    _wait_for_pyscript_init(docs_app_page, docs_console_messages)


@pytest.mark.e2e
def test_home_dropdown_follows_toggle_on_scroll(docs_app_page, assert_no_console_errors):
    dropdown_toggle = docs_app_page.locator("nav li a[aria-haspopup='true']").filter(has_text="Demos")
    dropdown_toggle.click()
    dropdown = docs_app_page.locator("ul.navbar-dropdown").filter(has_text="HelloWorld")
    expect(dropdown).to_be_visible()
    docs_app_page.evaluate("window.scrollTo(0, 200)")
    _wait_for_menu_aligned_with_toggle(docs_app_page, _demos_menu_id(docs_app_page))
    docs_app_page.evaluate("window.scrollTo(0, 0)")
    _wait_for_menu_aligned_with_toggle(docs_app_page, _demos_menu_id(docs_app_page))


def _demos_menu_id(page) -> str:
    toggle = page.locator("nav li a[aria-haspopup='true']").filter(has_text="Demos")
    menu_id = toggle.get_attribute("aria-controls")
    assert menu_id is not None
    return menu_id


def _wait_for_menu_aligned_with_toggle(page, menu_id: str):
    page.wait_for_function(
        "([menuId]) => {"
        "  const menu = document.getElementById(menuId);"
        "  const toggle = document.getElementById(menuId + '-toggle');"
        "  if (!menu || !toggle) return false;"
        "  const menu_rect = menu.getBoundingClientRect();"
        "  const toggle_rect = toggle.getBoundingClientRect();"
        "  return Math.abs(menu_rect.top - toggle_rect.bottom) < 2"
        "      && Math.abs(menu_rect.left - toggle_rect.left) < 2;"
        "}",
        arg=[menu_id],
    )


@pytest.mark.e2e
def test_home_dropdown_follows_toggle_on_resize(docs_app_page, assert_no_console_errors):
    dropdown_toggle = docs_app_page.locator("nav li a[aria-haspopup='true']").filter(has_text="Demos")
    dropdown_toggle.click()
    dropdown = docs_app_page.locator("ul.navbar-dropdown").filter(has_text="HelloWorld")
    expect(dropdown).to_be_visible()
    docs_app_page.set_viewport_size({"width": 1000, "height": 800})
    _wait_for_menu_aligned_with_toggle(docs_app_page, _demos_menu_id(docs_app_page))


@pytest.mark.e2e
def test_home_mobile_dropdown_spans_navbar_width(docs_app_page, assert_no_console_errors):
    docs_app_page.set_viewport_size({"width": 600, "height": 800})
    docs_app_page.locator("button.navbar-mobile-toggle").click()
    dropdown_toggle = docs_app_page.locator("nav li a[aria-haspopup='true']").filter(has_text="Demos")
    dropdown_toggle.click()
    dropdown = docs_app_page.locator("ul.navbar-dropdown").filter(has_text="HelloWorld")
    expect(dropdown).to_be_visible()
    menu_id = _demos_menu_id(docs_app_page)
    assert (
        docs_app_page.evaluate("menuId => getComputedStyle(document.getElementById(menuId)).position", menu_id)
        == "fixed"
    )
    box = dropdown.bounding_box()
    assert box is not None
    assert box["x"] == 0
    assert box["width"] == 600
