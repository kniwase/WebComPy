import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_nested_repeat_in_switch_initial_list_view(page_on):
    page = page_on("/nested-dynamic")
    expect(page.locator("[data-testid='nested-dynamic-page']")).to_be_visible()
    expect(page.locator("[data-testid='list-view']")).to_be_visible()
    expect(page.locator("[data-testid='grid-view']")).to_have_count(0)
    expect(page.locator("[data-testid='list-item']")).to_have_count(3)


def test_nested_repeat_in_switch_switch_to_grid(page_on):
    page = page_on("/nested-dynamic")
    expect(page.locator("[data-testid='list-view']")).to_be_visible()

    page.locator("[data-testid='grid-btn']").click()
    expect(page.locator("[data-testid='grid-view']")).to_be_visible()
    expect(page.locator("[data-testid='list-view']")).to_have_count(0)
    expect(page.locator("[data-testid='grid-item']")).to_have_count(3)


def test_nested_repeat_in_switch_switch_back_to_list(page_on):
    page = page_on("/nested-dynamic")
    page.locator("[data-testid='grid-btn']").click()
    expect(page.locator("[data-testid='grid-view']")).to_be_visible()

    page.locator("[data-testid='list-btn']").click()
    expect(page.locator("[data-testid='list-view']")).to_be_visible()
    expect(page.locator("[data-testid='grid-view']")).to_have_count(0)
    expect(page.locator("[data-testid='list-item']")).to_have_count(3)


def test_nested_repeat_in_switch_add_item(page_on):
    page = page_on("/nested-dynamic")
    page.locator("[data-testid='new-item-input']").fill("Delta")
    page.locator("[data-testid='add-item-btn']").click()
    expect(page.locator("[data-testid='list-item']")).to_have_count(4)


def test_nested_repeat_in_switch_add_then_switch(page_on):
    page = page_on("/nested-dynamic")
    page.locator("[data-testid='new-item-input']").fill("Delta")
    page.locator("[data-testid='add-item-btn']").click()
    expect(page.locator("[data-testid='list-item']")).to_have_count(4)

    page.locator("[data-testid='grid-btn']").click()
    expect(page.locator("[data-testid='grid-item']")).to_have_count(4)


def test_nested_repeat_in_switch_remove_first(page_on):
    page = page_on("/nested-dynamic")
    expect(page.locator("[data-testid='list-item']")).to_have_count(3)

    page.locator("[data-testid='remove-first-btn']").click()
    expect(page.locator("[data-testid='list-item']")).to_have_count(2)
