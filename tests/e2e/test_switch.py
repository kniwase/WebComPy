import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_switch_default_state(page_on):
    page = page_on("/switch")
    expect(page.locator("[data-testid='switch-page']")).to_be_visible()
    expect(page.locator("[data-testid='switch-on']")).to_be_visible()
    expect(page.locator("[data-testid='switch-off']")).to_have_count(0)
    expect(page.locator("[data-testid='flag-state']")).to_have_text("on")


def test_switch_toggle(page_on):
    page = page_on("/switch")
    page.locator("[data-testid='toggle-btn']").click()

    expect(page.locator("[data-testid='switch-on']")).to_have_count(0)
    expect(page.locator("[data-testid='switch-off']")).to_be_visible()
    expect(page.locator("[data-testid='flag-state']")).to_have_text("off")


def test_switch_toggle_back(page_on):
    page = page_on("/switch")
    page.locator("[data-testid='toggle-btn']").click()
    page.locator("[data-testid='toggle-btn']").click()

    expect(page.locator("[data-testid='switch-on']")).to_be_visible()
    expect(page.locator("[data-testid='switch-off']")).to_have_count(0)
    expect(page.locator("[data-testid='flag-state']")).to_have_text("on")
