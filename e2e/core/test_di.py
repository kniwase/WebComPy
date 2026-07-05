import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_provide_inject_from_parent(page_on):
    page = page_on("/di-provide")
    expect(page.locator("[data-testid='di-provider-page']")).to_be_visible()
    expect(page.locator("[data-testid='child-theme']")).to_have_text("dark-theme")


def test_inject_from_app_level(page_on):
    page = page_on("/di-inject")
    expect(page.locator("[data-testid='di-inject-page']")).to_be_visible()
    expect(page.locator("[data-testid='injected-app-theme']")).to_have_text("app-dark-theme")


def test_di_provide_inject_no_python_errors(page_on, assert_no_console_errors):
    page = page_on("/di-provide")
    expect(page.locator("[data-testid='child-theme']")).to_be_visible()


def test_di_navigation_no_python_errors(app_page, assert_no_console_errors):
    expect(app_page.locator("[data-testid='home-page']")).to_be_visible()
    app_page.locator("[data-testid='nav-di']").click()
    expect(app_page.locator("[data-testid='di-provider-page']")).to_be_visible()
    expect(app_page.locator("[data-testid='child-theme']")).to_have_text("dark-theme")


def test_di_home_then_navigate_then_back(app_page, assert_no_console_errors):
    expect(app_page.locator("[data-testid='home-page']")).to_be_visible()
    app_page.locator("[data-testid='nav-di']").click()
    expect(app_page.locator("[data-testid='di-provider-page']")).to_be_visible()
    app_page.locator("[data-testid='nav-home']").click()
    expect(app_page.locator("[data-testid='home-page']")).to_be_visible()
