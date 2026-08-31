"""E2E tests for the ui-form-controls docs demo page."""

import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe

pytestmark = pytest.mark.e2e


def test_ui_form_controls_page_loads(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/ui-form-controls")
    expect(page.locator("h1.page-title")).to_have_text("UI Form Controls")


def test_ui_form_controls_demo_validation_flow(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/ui-form-controls")
    frame = _wait_for_demo_iframe(page, "ui_form_controls")

    first_field = frame.locator(".webcompy-form-field").first
    name_input = first_field.locator("input")
    expect(first_field.locator("[role='alert']")).to_have_text("")

    name_input.click()
    name_input.fill("al")
    name_input.blur()
    expect(first_field.locator("[role='alert']")).to_have_text("At least 3 characters")
    assert name_input.get_attribute("aria-invalid") == "true"
    assert name_input.get_attribute("data-state") == "invalid"

    name_input.fill("alice")
    expect(first_field.locator("[role='alert']")).to_have_text("")


def test_ui_form_controls_demo_switch_and_submit(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/ui-form-controls")
    frame = _wait_for_demo_iframe(page, "ui_form_controls")

    name_input = frame.locator(".webcompy-form-field input").first
    email_input = frame.locator(".webcompy-form-field input").nth(1)
    name_input.fill("alice")
    email_input.fill("alice@example.com")
    frame.locator(".webcompy-form-field select").select_option("jp")
    frame.locator("input[type='checkbox']").last.check()
    switch = frame.locator("input[role='switch']").first
    expect(switch).to_have_attribute("aria-checked", "true")
    switch.click()
    expect(switch).to_have_attribute("aria-checked", "false")

    frame.locator("#ufc-demo-submit").click()
    expect(frame.locator("#ufc-demo-status")).to_have_text("Welcome, alice (free plan)!")

    frame.locator("#ufc-demo-reset").click()
    expect(frame.locator("#ufc-demo-status")).to_have_text("")
    expect(name_input).to_have_value("")
