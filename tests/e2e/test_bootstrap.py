import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_app_loads(app_page, assert_no_python_errors):
    expect(app_page.locator("#webcompy-app")).to_be_visible()


def test_loading_screen_removed(app_page, assert_no_python_errors):
    loading = app_page.locator("#webcompy-loading")
    expect(loading).to_have_count(0)


def test_home_page_rendered(app_page, assert_no_python_errors):
    expect(app_page.locator("[data-testid='home-page']")).to_be_visible()
    expect(app_page.locator("[data-testid='home-page'] h1")).to_have_text("E2E Test App")


def test_page_title(app_page, assert_no_python_errors):
    expect(app_page).to_have_title("Home - E2E")
