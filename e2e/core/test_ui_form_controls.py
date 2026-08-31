"""E2E tests for ui form controls (themed headless pairs in a real browser)."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def _wait_page(page_on):
    page = page_on("/ui-form-controls")
    expect(page.locator("[data-testid='ui-form-controls-page']")).to_be_visible()
    return page


def test_label_association_via_form_field(page_on):
    page = _wait_page(page_on)
    name_field = page.locator(".ufc-name-field")
    label_for = name_field.locator("label").first.get_attribute("for")
    assert label_for
    associated = page.locator(f"input#{label_for}")
    expect(associated).to_have_count(1)
    expect(name_field.locator("input")).to_have_count(1)


def test_errors_hidden_until_touched(page_on):
    page = _wait_page(page_on)
    name_input = page.locator(".ufc-name-field input")
    error_region = page.locator(".ufc-name-field [role='alert']")
    expect(error_region).to_have_text("")
    assert name_input.get_attribute("aria-invalid") is None

    name_input.click()
    name_input.blur()
    expect(error_region).to_contain_text("This field is required")
    expect(error_region).to_contain_text("Must be at least 2 characters")
    assert name_input.get_attribute("aria-invalid") == "true"
    assert name_input.get_attribute("aria-describedby") == error_region.get_attribute("id")
    assert name_input.get_attribute("data-state") == "invalid"


def test_valid_input_clears_error(page_on):
    page = _wait_page(page_on)
    name_input = page.locator(".ufc-name-field input")
    name_input.fill("a")
    name_input.blur()
    expect(page.locator(".ufc-name-field [role='alert']")).to_have_text("Must be at least 2 characters")

    name_input.fill("alice")
    expect(page.locator(".ufc-name-field [role='alert']")).to_have_text("")
    assert name_input.get_attribute("data-state") == "valid"
    assert name_input.get_attribute("aria-describedby") is None


def test_select_binding(page_on):
    page = _wait_page(page_on)
    page.locator("[data-testid='ufc-submit']").click()
    country = page.locator(".ufc-country-field select")
    expect(page.locator(".ufc-country-field [role='alert']")).to_have_text("This field is required")
    assert country.get_attribute("data-state") == "invalid"

    country.select_option("jp")
    expect(page.locator(".ufc-country-field [role='alert']")).to_have_text("")
    assert country.get_attribute("data-state") == "valid"
    assert country.input_value() == "jp"


def test_switch_semantics(page_on):
    page = _wait_page(page_on)
    switch = page.locator(".ufc-notify-field input")
    assert switch.get_attribute("role") == "switch"
    assert switch.get_attribute("aria-checked") == "false"
    switch.click()
    expect(switch).to_have_attribute("aria-checked", "true")


def test_checkbox_error_gating(page_on):
    page = _wait_page(page_on)
    checkbox = page.locator(".ufc-agree-field input[type='checkbox']")
    checkbox.click()
    checkbox.click()
    checkbox.blur()
    expect(page.locator(".ufc-agree-field [role='alert']")).to_have_text("agree")
    assert checkbox.get_attribute("data-state") == "invalid"
    assert checkbox.get_attribute("aria-invalid") == "true"
    checkbox.click()
    expect(page.locator(".ufc-agree-field [role='alert']")).to_have_text("")
    assert checkbox.get_attribute("data-state") == "valid"


def test_radio_group_shared_name(page_on):
    page = _wait_page(page_on)
    radios = page.locator(".ufc-plan-field input[type='radio']")
    expect(radios).to_have_count(2)
    name = radios.first.get_attribute("name")
    assert name
    assert radios.nth(1).get_attribute("name") == name
    radios.nth(1).click()
    expect(radios.nth(1)).to_be_checked()


def test_submit_gating_and_reset(page_on):
    page = _wait_page(page_on)
    page.locator("[data-testid='ufc-submit']").click()
    expect(page.locator("[data-testid='ufc-status']")).to_have_text("idle")
    expect(page.locator(".ufc-name-field [role='alert']")).to_contain_text("This field is required")

    page.locator(".ufc-name-field input").fill("alice")
    page.locator(".ufc-country-field select").select_option("us")
    page.locator(".ufc-agree-field input").click()
    page.locator(".ufc-plan-field input[type='radio']").first.click()
    page.locator("[data-testid='ufc-submit']").click()
    expect(page.locator("[data-testid='ufc-status']")).to_have_text("submitted")

    page.locator("[data-testid='ufc-reset']").click()
    expect(page.locator("[data-testid='ufc-status']")).to_have_text("idle")
    expect(page.locator(".ufc-name-field input")).to_have_value("")
    expect(page.locator(".ufc-name-field [role='alert']")).to_have_text("")
    assert page.locator(".ufc-name-field input").get_attribute("aria-invalid") is None
