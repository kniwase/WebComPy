import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_repeat_initial_empty(page_on):
    page = page_on("/repeat")
    expect(page.locator("[data-testid='repeat-page']")).to_be_visible()
    expect(page.locator("[data-testid='list-item']")).to_have_count(0)


def test_repeat_add_items(page_on):
    page = page_on("/repeat")
    page.locator("[data-testid='add-btn']").click()
    expect(page.locator("[data-testid='list-item']")).to_have_count(1)
    expect(page.locator("[data-testid='list-item']").first).to_have_text("Item 1")

    page.locator("[data-testid='add-btn']").click()
    expect(page.locator("[data-testid='list-item']")).to_have_count(2)


def test_repeat_remove_items(page_on):
    page = page_on("/repeat")
    page.locator("[data-testid='add-btn']").click()
    page.locator("[data-testid='add-btn']").click()
    page.locator("[data-testid='add-btn']").click()
    expect(page.locator("[data-testid='list-item']")).to_have_count(3)

    page.locator("[data-testid='remove-btn']").click()
    expect(page.locator("[data-testid='list-item']")).to_have_count(2)

    page.locator("[data-testid='remove-btn']").click()
    expect(page.locator("[data-testid='list-item']")).to_have_count(1)

    page.locator("[data-testid='remove-btn']").click()
    expect(page.locator("[data-testid='list-item']")).to_have_count(0)
