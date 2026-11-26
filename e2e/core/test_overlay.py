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
    # Click at top-left corner of backdrop to avoid panel intercepting pointer events
    page.locator(".webcompy-modal-backdrop").click(position={"x": 5, "y": 5})
    expect(page.locator("[role='dialog']")).to_have_count(0)


def test_drawer_opens(page_on):
    page = page_on("/overlay")
    page.locator("[data-testid='open-drawer']").click()
    drawer = page.locator("[role='dialog']").last
    expect(drawer).to_be_visible()
    expect(drawer).to_have_attribute("data-edge", "right")


def test_dropdown_opens_and_shows_items(page_on):
    page = page_on("/overlay")
    trigger = page.locator("[data-testid='dropdown-wrapper'] button")
    trigger.click()
    expect(trigger).to_have_attribute("aria-expanded", "true")
    expect(page.locator("[role='menu']")).to_be_visible()
    expect(page.locator("[data-testid='dropdown-item-1']")).to_be_visible()


def test_dropdown_escape_closes(page_on):
    page = page_on("/overlay")
    trigger = page.locator("[data-testid='dropdown-wrapper'] button")
    trigger.click()
    expect(page.locator("[role='menu']")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("[role='menu']")).to_have_count(0)
    expect(trigger).to_have_attribute("aria-expanded", "false")


def test_dropdown_outside_click_closes(page_on):
    page = page_on("/overlay")
    trigger = page.locator("[data-testid='dropdown-wrapper'] button")
    trigger.click()
    expect(page.locator("[role='menu']")).to_be_visible()
    page.locator("[data-testid='outside-area']").click()
    expect(page.locator("[role='menu']")).to_have_count(0)


def test_multi_dropdowns_have_distinct_ids_and_open_independently(page_on):
    page = page_on("/overlay")
    trigger_a = page.locator("[data-testid='dropdown-a'] button")
    trigger_b = page.locator("[data-testid='dropdown-b'] button")
    trigger_a.click()
    expect(trigger_a).to_have_attribute("aria-expanded", "true")
    expect(page.locator("[data-testid='dropdown-a-item']")).to_be_visible()
    # Activating the sibling dropdown closes the open one (capture-phase outside close)
    trigger_b.click()
    expect(trigger_b).to_have_attribute("aria-expanded", "true")
    expect(trigger_a).to_have_attribute("aria-expanded", "false")
    expect(page.locator("[data-testid='dropdown-b-item']")).to_be_visible()
    expect(page.locator("[data-testid='dropdown-a-item']")).to_have_count(0)
    # Instance DOM ids are unique and aria-controls pairs with its own menu
    ids = page.evaluate(
        "() => {"
        "  const buttons = [...document.querySelectorAll('[data-testid=\\'dropdown-multi-wrapper\\'] button')];"
        "  return buttons.map((b) => ({id: b.id, controls: b.getAttribute('aria-controls')}));"
        "}"
    )
    assert ids[0]["id"] != ids[1]["id"]
    assert ids[0]["controls"] != ids[1]["controls"]


def test_toast_push_and_visible(page_on):
    page = page_on("/overlay")
    page.locator("[data-testid='push-toast']").click()
    toast = page.locator("[data-state='visible']").first
    expect(toast).to_be_visible()
    expect(toast).to_contain_text("Toast message")


def test_modal_and_drawer_dark_mode_backdrop_and_panel_styles(page, page_on):
    page.emulate_media(color_scheme="dark")
    page_on("/overlay")

    page.locator("[data-testid='open-modal']").click()
    modal_backdrop = page.locator(".webcompy-modal-backdrop")
    modal_panel = page.locator(".webcompy-modal-panel")
    expect(modal_backdrop).to_be_visible()
    expect(modal_panel).to_be_visible()
    modal_styles = page.evaluate(
        "() => {"
        "  const b = getComputedStyle(document.querySelector('.webcompy-modal-backdrop'));"
        "  const p = getComputedStyle(document.querySelector('.webcompy-modal-panel'));"
        "  return { bBg: b.backgroundColor, bOp: b.opacity, pBg: p.backgroundColor, pFg: p.color, pShadow: p.boxShadow };"
        "}"
    )
    assert modal_styles["bOp"] == "1"
    assert modal_styles["bBg"] in ("rgba(0, 0, 0, 0.5)", "rgb(0, 0, 0)")
    assert modal_styles["pShadow"] != "none"
    assert modal_styles["pBg"] != modal_styles["pFg"]
    page.keyboard.press("Escape")
    expect(page.locator("[role='dialog']")).to_have_count(0)

    page.locator("[data-testid='open-drawer']").click()
    drawer_backdrop = page.locator(".webcompy-drawer-backdrop")
    drawer_panel = page.locator(".webcompy-drawer-panel")
    expect(drawer_backdrop).to_be_visible()
    expect(drawer_panel).to_be_visible()
    drawer_styles = page.evaluate(
        "() => {"
        "  const b = getComputedStyle(document.querySelector('.webcompy-drawer-backdrop'));"
        "  const p = getComputedStyle(document.querySelector('.webcompy-drawer-panel'));"
        "  return {"
        "    bBg: b.backgroundColor,"
        "    pPadTop: parseFloat(p.paddingTop),"
        "    pPadLeft: parseFloat(p.paddingLeft),"
        "    pBg: p.backgroundColor,"
        "    pFg: p.color,"
        "    pShadow: p.boxShadow,"
        "  };"
        "}"
    )
    assert drawer_styles["bBg"] in ("rgba(0, 0, 0, 0.5)", "rgb(0, 0, 0)")
    assert drawer_styles["pPadTop"] > 0
    assert drawer_styles["pPadLeft"] > 0
    assert drawer_styles["pShadow"] != "none"
    assert drawer_styles["pBg"] != drawer_styles["pFg"]
    drawer_backdrop.click(position={"x": 5, "y": 5})
    expect(page.locator("[role='dialog']")).to_have_count(0)
