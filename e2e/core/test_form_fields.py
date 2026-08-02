import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_errors_hidden_until_touched(page_on):
    page = page_on("/form-fields")
    expect(page.locator("[data-testid='form-fields-page']")).to_be_visible()

    expect(page.locator("[data-testid='ff-email-error']")).to_have_text("")
    expect(page.locator("[data-testid='ff-password-error']")).to_have_text("")

    page.locator("[data-testid='ff-email']").fill("not-an-email")
    page.locator("[data-testid='ff-email']").blur()
    expect(page.locator("[data-testid='ff-email-error']")).not_to_have_text("")

    page.locator("[data-testid='ff-password']").fill("short")
    page.locator("[data-testid='ff-password']").blur()
    expect(page.locator("[data-testid='ff-password-error']")).not_to_have_text("")


def test_valid_input_clears_error(page_on):
    page = page_on("/form-fields")
    expect(page.locator("[data-testid='form-fields-page']")).to_be_visible()

    page.locator("[data-testid='ff-email']").fill("not-an-email")
    page.locator("[data-testid='ff-email']").blur()
    expect(page.locator("[data-testid='ff-email-error']")).not_to_have_text("")

    page.locator("[data-testid='ff-email']").fill("alice@example.com")
    expect(page.locator("[data-testid='ff-email-error']")).to_have_text("")


def test_dirty_tracking(page_on):
    page = page_on("/form-fields")
    expect(page.locator("[data-testid='form-fields-page']")).to_be_visible()

    expect(page.locator("[data-testid='ff-form-dirty']")).to_have_text("clean")
    page.locator("[data-testid='ff-email']").fill("alice@example.com")
    expect(page.locator("[data-testid='ff-form-dirty']")).to_have_text("dirty")


def test_submit_blocked_when_invalid(page_on):
    page = page_on("/form-fields")
    expect(page.locator("[data-testid='form-fields-page']")).to_be_visible()

    page.locator("[data-testid='ff-submit']").click()
    expect(page.locator("[data-testid='ff-email-error']")).not_to_have_text("")
    expect(page.locator("[data-testid='ff-password-error']")).not_to_have_text("")
    expect(page.locator("[data-testid='ff-status']")).to_have_text("")


def test_successful_submit(page_on):
    page = page_on("/form-fields")
    expect(page.locator("[data-testid='form-fields-page']")).to_be_visible()

    page.locator("[data-testid='ff-email']").fill("alice@example.com")
    page.locator("[data-testid='ff-password']").fill("secret123")
    page.locator("[data-testid='ff-submit']").click()
    expect(page.locator("[data-testid='ff-status']")).to_have_text("logged-in")
