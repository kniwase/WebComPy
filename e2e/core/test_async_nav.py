import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_async_nav_via_router_link(app_page):
    app_page.locator("[data-testid='nav-async-nav']").click()
    expect(app_page.locator("[data-testid='async-nav-page']")).to_be_visible()
    expect(app_page.locator("[data-testid='async-message']")).to_have_text("Hello from async navigation!")
    expect(app_page.locator("[data-testid='async-item-count']")).to_have_text("3")


def test_async_nav_direct_url(page_on):
    page = page_on("/async-nav")
    expect(page.locator("[data-testid='async-nav-page']")).to_be_visible()
    expect(page.locator("[data-testid='async-message']")).to_have_text("Hello from async navigation!")
    expect(page.locator("[data-testid='async-item-count']")).to_have_text("3")


def test_async_nav_navigate_away_and_back(app_page):
    app_page.locator("[data-testid='nav-async-nav']").click()
    expect(app_page.locator("[data-testid='async-nav-page']")).to_be_visible()
    expect(app_page.locator("[data-testid='async-message']")).to_have_text("Hello from async navigation!")

    app_page.locator("[data-testid='nav-home']").click()
    expect(app_page.locator("[data-testid='async-nav-page']")).to_have_count(0)

    app_page.locator("[data-testid='nav-async-nav']").click()
    expect(app_page.locator("[data-testid='async-nav-page']")).to_be_visible()
    expect(app_page.locator("[data-testid='async-message']")).to_have_text("Hello from async navigation!")
    expect(app_page.locator("[data-testid='async-item-count']")).to_have_text("3")
