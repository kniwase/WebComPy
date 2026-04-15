import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_click_event_handler(page_on):
    page = page_on("/event")
    expect(page.locator("[data-testid='event-page']")).to_be_visible()

    expect(page.locator("[data-testid='click-count']")).to_have_text("0")

    page.locator("[data-testid='click-btn']").click()
    expect(page.locator("[data-testid='click-count']")).to_have_text("1")

    page.locator("[data-testid='click-btn']").click()
    page.locator("[data-testid='click-btn']").click()
    expect(page.locator("[data-testid='click-count']")).to_have_text("3")


def test_input_and_dom_node_ref(page_on):
    page = page_on("/event")
    expect(page.locator("[data-testid='event-page']")).to_be_visible()

    page.locator("[data-testid='text-input']").fill("hello")
    page.locator("[data-testid='submit-btn']").click()
    expect(page.locator("[data-testid='input-value']")).to_have_text("hello")


def test_checkbox_and_change_event(page_on):
    page = page_on("/event")
    expect(page.locator("[data-testid='event-page']")).to_be_visible()

    expect(page.locator("[data-testid='checkbox-state']")).to_have_text("unchecked")

    page.locator("[data-testid='checkbox-input']").check()
    expect(page.locator("[data-testid='checkbox-state']")).to_have_text("checked")

    page.locator("[data-testid='checkbox-input']").uncheck()
    expect(page.locator("[data-testid='checkbox-state']")).to_have_text("unchecked")
