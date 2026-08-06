import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_scroll_restoration_push_top_and_back_restore(page_on):
    page = page_on("/scroll-long")
    expect(page.locator("[data-testid='scroll-long-page']")).to_be_visible()

    page.locator("[data-testid='scroll-nav-target']").scroll_into_view_if_needed()
    page.wait_for_function("window.scrollY > 0")
    saved_y = page.evaluate("window.scrollY")

    page.locator("[data-testid='scroll-nav-target']").click()
    expect(page.locator("[data-testid='scroll-target-page']")).to_be_visible()
    page.wait_for_function("window.scrollY === 0")

    page.go_back()
    expect(page.locator("[data-testid='scroll-long-page']")).to_be_visible()
    page.wait_for_function(f"Math.abs(window.scrollY - {saved_y}) < 50")
