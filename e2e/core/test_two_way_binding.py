import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_text_input_two_way(page_on):
    page = page_on("/two-way-binding")
    expect(page.locator("[data-testid='two-way-binding-page']")).to_be_visible()

    expect(page.locator("[data-testid='bind-text']")).to_have_value("hello")
    expect(page.locator("[data-testid='bind-text-value']")).to_have_text("hello")

    page.locator("[data-testid='bind-text']").fill("world")
    expect(page.locator("[data-testid='bind-text-value']")).to_have_text("world")


def test_text_signal_to_dom(page_on):
    page = page_on("/two-way-binding")
    expect(page.locator("[data-testid='two-way-binding-page']")).to_be_visible()

    page.locator("[data-testid='set-text-btn']").click()
    expect(page.locator("[data-testid='bind-text']")).to_have_value("reset")
    expect(page.locator("[data-testid='bind-text-value']")).to_have_text("reset")


def test_number_input_two_way(page_on):
    page = page_on("/two-way-binding")
    expect(page.locator("[data-testid='two-way-binding-page']")).to_be_visible()

    expect(page.locator("[data-testid='bind-number']")).to_have_value("5")

    page.locator("[data-testid='bind-number']").fill("42")
    expect(page.locator("[data-testid='bind-number-value']")).to_have_text("42")

    page.locator("[data-testid='bind-number']").fill("")
    expect(page.locator("[data-testid='bind-number-value']")).to_have_text("42")


def test_checkbox_two_way(page_on):
    page = page_on("/two-way-binding")
    expect(page.locator("[data-testid='two-way-binding-page']")).to_be_visible()

    expect(page.locator("[data-testid='bind-checkbox-value']")).to_have_text("unchecked")

    page.locator("[data-testid='bind-checkbox']").check()
    expect(page.locator("[data-testid='bind-checkbox-value']")).to_have_text("checked")

    page.locator("[data-testid='bind-checkbox']").uncheck()
    expect(page.locator("[data-testid='bind-checkbox-value']")).to_have_text("unchecked")


def test_radio_group_two_way(page_on):
    page = page_on("/two-way-binding")
    expect(page.locator("[data-testid='two-way-binding-page']")).to_be_visible()

    expect(page.locator("[data-testid='bind-radio-a']")).to_be_checked()
    expect(page.locator("[data-testid='bind-radio-value']")).to_have_text("a")

    page.locator("[data-testid='bind-radio-b']").check()
    expect(page.locator("[data-testid='bind-radio-a']")).not_to_be_checked()
    expect(page.locator("[data-testid='bind-radio-b']")).to_be_checked()
    expect(page.locator("[data-testid='bind-radio-value']")).to_have_text("b")


def test_textarea_two_way(page_on):
    page = page_on("/two-way-binding")
    expect(page.locator("[data-testid='two-way-binding-page']")).to_be_visible()

    expect(page.locator("[data-testid='bind-textarea']")).to_have_value("initial")

    page.locator("[data-testid='bind-textarea']").fill("typed body")
    expect(page.locator("[data-testid='bind-textarea-value']")).to_have_text("typed body")
