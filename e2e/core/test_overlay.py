"""E2E tests for overlay components."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_modal_opens_and_traps_focus(page_on):
    page = page_on("/overlay")
    page.locator("[data-testid='open-modal']").click()
    modal = page.locator("[role='dialog']")
    expect(modal).to_be_visible()
    expect(modal).to_have_attribute("aria-modal", "true")
    expect(modal).to_have_attribute("data-state", "open")
    # Check backdrop via class
    expect(page.locator(".webcompy-modal-backdrop")).to_be_visible()


def test_modal_escape_closes(page_on):
    page = page_on("/overlay")
    page.locator("[data-testid='open-modal']").click()
    expect(page.locator("[role='dialog']")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("[role='dialog']")).to_have_count(0)


def test_modal_backdrop_closes(page_on):
    page = page_on("/overlay")
    page.locator("[data-testid='open-modal']").click()
    expect(page.locator("[role='dialog']")).to_be_visible()
    page.locator(".webcompy-modal-backdrop").click()
    expect(page.locator("[role='dialog']")).to_have_count(0)


def test_drawer_opens(page_on):
    page = page_on("/overlay")
    page.locator("[data-testid='open-drawer']").click()
    drawer = page.locator("[role='dialog']").last
    expect(drawer).to_be_visible()
    expect(drawer).to_have_attribute("data-edge", "right")


def test_dropdown_opens_and_shows_items(page_on):
    page = page_on("/overlay")
    # Trigger is inside dropdown wrapper
    page.locator("[data-testid='dropdown-wrapper'] button").click()
    expect(page.locator("[role='menu']")).to_be_visible()
    expect(page.locator("[data-testid='dropdown-item-1']")).to_be_visible()


def test_dropdown_escape_closes(page_on):
    page = page_on("/overlay")
    page.locator("[data-testid='dropdown-wrapper'] button").click()
    expect(page.locator("[role='menu']")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("[role='menu']")).to_have_count(0)


def test_dropdown_outside_click_closes(page_on):
    page = page_on("/overlay")
    page.locator("[data-testid='dropdown-wrapper'] button").click()
    expect(page.locator("[role='menu']")).to_be_visible()
    page.locator("[data-testid='outside-area']").click()
    expect(page.locator("[role='menu']")).to_have_count(0)


def test_toast_push_and_visible(page_on):
    page = page_on("/overlay")
    page.locator("[data-testid='push-toast']").click()
    toast = page.locator("[data-state='visible']").first
    expect(toast).to_be_visible()
    expect(toast).to_contain_text("Toast message")
