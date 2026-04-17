import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_keyed_repeat_initial_empty(page_on):
    page = page_on("/keyed-repeat")
    expect(page.locator("[data-testid='keyed-repeat-page']")).to_be_visible()
    expect(page.locator("[data-testid='keyed-list-item']")).to_have_count(0)


def test_keyed_repeat_add_items(page_on):
    page = page_on("/keyed-repeat")
    page.locator("[data-testid='keyed-add-btn']").click()
    expect(page.locator("[data-testid='keyed-list-item']")).to_have_count(1)

    page.locator("[data-testid='keyed-add-btn']").click()
    expect(page.locator("[data-testid='keyed-list-item']")).to_have_count(2)


def test_keyed_repeat_remove_first(page_on):
    page = page_on("/keyed-repeat")
    page.locator("[data-testid='keyed-add-btn']").click()
    page.locator("[data-testid='keyed-add-btn']").click()
    page.locator("[data-testid='keyed-add-btn']").click()
    expect(page.locator("[data-testid='keyed-list-item']")).to_have_count(3)

    page.locator("[data-testid='keyed-remove-first-btn']").click()
    expect(page.locator("[data-testid='keyed-list-item']")).to_have_count(2)


def test_keyed_repeat_insert_at_start(page_on):
    page = page_on("/keyed-repeat")
    page.locator("[data-testid='keyed-add-btn']").click()
    page.locator("[data-testid='keyed-add-btn']").click()
    expect(page.locator("[data-testid='keyed-list-item']")).to_have_count(2)

    page.locator("[data-testid='keyed-add-start-btn']").click()
    expect(page.locator("[data-testid='keyed-list-item']")).to_have_count(3)


def test_keyed_repeat_input_preserved_after_add(page_on):
    page = page_on("/keyed-repeat")
    page.locator("[data-testid='keyed-add-btn']").click()
    page.locator("[data-testid='keyed-add-btn']").click()
    page.locator("[data-testid='keyed-input']").first.fill("typed-hello")

    page.locator("[data-testid='keyed-add-btn']").click()
    expect(page.locator("[data-testid='keyed-list-item']")).to_have_count(3)

    first_input = page.locator("[data-testid='keyed-input']").first
    expect(first_input).to_have_value("typed-hello")
