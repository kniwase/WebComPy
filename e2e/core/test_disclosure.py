"""E2E tests for disclosure and feedback components."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def _tabs(page):
    return page.locator("[role='tab']")


def _panels(page):
    return page.locator("[role='tabpanel']")


def test_tabs_initial_state(page_on):
    page = page_on("/disclosure")
    expect(_tabs(page)).to_have_count(3)
    expect(_tabs(page).nth(0)).to_have_attribute("aria-selected", "true")
    expect(_tabs(page).nth(0)).to_have_attribute("data-state", "active")
    expect(_tabs(page).nth(0)).to_have_attribute("tabindex", "0")
    expect(_tabs(page).nth(1)).to_have_attribute("tabindex", "-1")
    expect(page.locator("[data-testid='panel-b']")).to_be_hidden()


def test_tabs_click_switch(page_on):
    page = page_on("/disclosure")
    page.locator("[role='tab']").filter(has_text="Beta").click()
    expect(_tabs(page).nth(1)).to_have_attribute("aria-selected", "true")
    expect(page.locator("[data-testid='panel-a']")).to_be_hidden()
    expect(page.locator("[data-testid='panel-b']")).to_be_visible()


def test_tabs_keyboard_navigation_wraps_and_activates(page_on):
    page = page_on("/disclosure")
    last = page.locator("[role='tab']").filter(has_text="Gamma")
    last.click()
    expect(last).to_have_attribute("aria-selected", "true")
    page.keyboard.press("ArrowRight")
    first = page.locator("[role='tab']").filter(has_text="Alpha")
    expect(first).to_have_attribute("aria-selected", "true")
    focused_text = page.evaluate("document.activeElement.textContent")
    assert focused_text == "Alpha"
    page.keyboard.press("ArrowLeft")
    expect(last).to_have_attribute("aria-selected", "true")


def test_tabs_panel_state_preservation(page_on):
    page = page_on("/disclosure")
    input_a = page.locator("[data-testid='tab-input-a']")
    input_a.fill("kept text")
    page.locator("[role='tab']").filter(has_text="Beta").click()
    expect(input_a).to_be_hidden()
    page.locator("[role='tab']").filter(has_text="Alpha").click()
    expect(input_a).to_have_value("kept text")


def test_collapse_expand_and_collapse(page_on):
    page = page_on("/disclosure")
    trigger = page.locator("[data-testid='disclosure-page'] button").filter(has_text="Toggle details")
    expect(trigger).to_have_attribute("aria-expanded", "false")
    expect(page.locator("[data-testid='collapse-body']")).to_have_count(0)
    trigger.click()
    body = page.locator("[data-testid='collapse-body']")
    expect(body).to_be_visible()
    expect(trigger).to_have_attribute("aria-expanded", "true")
    expect(trigger).to_have_attribute("data-state", "open")
    expect(page.locator(".webcompy-collapse-content")).to_have_css("display", "grid")
    trigger.click()
    expect(page.locator("[data-testid='collapse-body']")).to_have_count(0)
    expect(trigger).to_have_attribute("data-state", "closed")


def test_accordion_single_open(page_on):
    page = page_on("/disclosure")
    page.locator("[data-testid='disclosure-page'] button").filter(has_text="First").click()
    expect(page.locator("[data-testid='acc-body-1']")).to_be_visible()
    page.locator("[data-testid='disclosure-page'] button").filter(has_text="Second").click()
    expect(page.locator("[data-testid='acc-body-2']")).to_be_visible()
    expect(page.locator("[data-testid='acc-body-1']")).to_have_count(0)


def test_alert_dismiss(page_on):
    page = page_on("/disclosure")
    alert = page.get_by_role("alert")
    expect(alert).to_be_visible()
    alert.get_by_role("button", name="Dismiss").click()
    expect(alert).to_be_hidden()


def test_progress_determinate_updates(page_on):
    page = page_on("/disclosure")
    bar = page.get_by_role("progressbar", name="Upload progress")
    expect(bar).to_have_attribute("aria-valuenow", "20")
    expect(bar).to_have_attribute("data-state", "determinate")
    page.locator("[data-testid='bump-progress']").click()
    expect(bar).to_have_attribute("aria-valuenow", "40")
    indeterminate = page.get_by_role("progressbar", name="Loading")
    expect(indeterminate).to_have_attribute("data-state", "indeterminate")
    assert indeterminate.get_attribute("aria-valuenow") is None


def test_badge_and_card_render(page_on):
    page = page_on("/disclosure")
    badge = page.locator("[data-testid='badge-row'] span")
    expect(badge).to_be_visible()
    expect(badge).to_have_attribute("data-variant", "success")
    expect(page.get_by_text("Card title")).to_be_visible()
    expect(page.get_by_text("Card body")).to_be_visible()
    expect(page.get_by_text("Card footer")).to_be_visible()
