import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe

pytestmark = pytest.mark.e2e


def test_examples_forms_page_loads_and_submit_role(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/forms")
    assert page.title() == "Forms - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text("Forms")
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()

    frame = _wait_for_demo_iframe(page, "ui_form_controls")
    expect(frame.get_by_role("button", name="Submit")).to_be_visible()


def test_examples_forms_validation_flow(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/forms")
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


def test_examples_forms_switch_and_submit(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/forms")
    frame = _wait_for_demo_iframe(page, "ui_form_controls")

    name_input = frame.locator(".webcompy-form-field input").first
    email_input = frame.locator(".webcompy-form-field input").nth(1)
    name_input.fill("alice")
    email_input.fill("alice@example.com")
    frame.locator(".webcompy-form-field select").select_option("jp")
    frame.locator("input.webcompy-checkbox").check()
    switch = frame.locator("input[role='switch']").first
    expect(switch).to_have_attribute("aria-checked", "true")
    switch.click()
    expect(switch).to_have_attribute("aria-checked", "false")

    frame.get_by_role("button", name="Submit").click()
    expect(frame.locator("#ufc-demo-status")).to_have_text("Welcome, alice (free plan)!")

    frame.get_by_role("button", name="Reset").click()
    expect(frame.locator("#ufc-demo-status")).to_have_text("")
    expect(name_input).to_have_value("")
