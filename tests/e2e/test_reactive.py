import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_reactive_text_update(page_on):
    page = page_on("/reactive")
    expect(page.locator("[data-testid='reactive-page']")).to_be_visible()

    expect(page.locator("[data-testid='count']")).to_have_text("0")
    expect(page.locator("[data-testid='doubled']")).to_have_text("0")

    page.locator("[data-testid='increment-btn']").click()
    expect(page.locator("[data-testid='count']")).to_have_text("1")
    expect(page.locator("[data-testid='doubled']")).to_have_text("2")

    page.locator("[data-testid='increment-btn']").click()
    expect(page.locator("[data-testid='count']")).to_have_text("2")
    expect(page.locator("[data-testid='doubled']")).to_have_text("4")

    page.locator("[data-testid='decrement-btn']").click()
    expect(page.locator("[data-testid='count']")).to_have_text("1")
    expect(page.locator("[data-testid='doubled']")).to_have_text("2")


def test_reactive_list_operations(page_on):
    page = page_on("/reactive")
    expect(page.locator("[data-testid='reactive-page']")).to_be_visible()

    expect(page.locator("[data-testid='list-count']")).to_have_text("3")

    page.locator("[data-testid='list-add-btn']").click()
    expect(page.locator("[data-testid='list-count']")).to_have_text("4")

    page.locator("[data-testid='list-remove-btn']").click()
    expect(page.locator("[data-testid='list-count']")).to_have_text("3")


def test_reactive_dict_operations(page_on):
    page = page_on("/reactive")
    expect(page.locator("[data-testid='reactive-page']")).to_be_visible()

    expect(page.locator("[data-testid='dict-count']")).to_have_text("1")

    page.locator("[data-testid='dict-add-btn']").click()
    expect(page.locator("[data-testid='dict-count']")).to_have_text("2")
