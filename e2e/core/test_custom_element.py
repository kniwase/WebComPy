import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_custom_element_defined_and_count(page_on):
    page = page_on("/custom-elements")
    expect(page.locator("[data-testid='custom-element-page']")).to_be_visible()
    defined = page.evaluate(
        "() => { const cls = customElements.get('e2e-card');"
        " return cls !== undefined && cls !== null && typeof cls === 'function'; }"
    )
    assert defined
    expect(page.locator("e2e-card")).to_have_count(2)


def test_multi_root_structure(page_on):
    page = page_on("/custom-elements")
    card = page.locator("e2e-card").first
    expect(card.locator(":scope > header")).to_have_count(1)
    expect(card.locator(":scope > main")).to_have_count(1)
    expect(card.locator(":scope > footer")).to_have_count(1)


def test_mounted_fires_once_per_card_on_load(page_on):
    page = page_on("/custom-elements")
    expect(page.locator("[data-testid='mounted-total']")).to_have_text("2")
    expect(page.locator("[data-testid='unmounted-total']")).to_have_text("0")


def test_same_document_reorder_fires_no_hooks(page_on):
    page = page_on("/custom-elements")
    expect(page.locator("[data-testid='mounted-total']")).to_have_text("2")
    page.locator("[data-testid='reverse-btn']").click()
    expect(page.locator("[data-testid='mounted-total']")).to_have_text("2")
    expect(page.locator("[data-testid='unmounted-total']")).to_have_text("0")


def test_remove_fires_unmounted(page_on):
    page = page_on("/custom-elements")
    expect(page.locator("[data-testid='mounted-total']")).to_have_text("2")
    page.locator("[data-testid='remove-btn']").click()
    expect(page.locator("e2e-card")).to_have_count(1)
    expect(page.locator("[data-testid='mounted-total']")).to_have_text("2")
    expect(page.locator("[data-testid='unmounted-total']")).to_have_text("1")


def test_add_fires_mounted(page_on):
    page = page_on("/custom-elements")
    expect(page.locator("[data-testid='mounted-total']")).to_have_text("2")
    page.locator("[data-testid='add-btn']").click()
    expect(page.locator("e2e-card")).to_have_count(3)
    expect(page.locator("[data-testid='mounted-total']")).to_have_text("3")
    expect(page.locator("[data-testid='unmounted-total']")).to_have_text("0")


def test_external_attribute_change_updates_props(page_on):
    page = page_on("/custom-elements")
    card = page.locator("e2e-card").first
    theme = card.locator("[data-testid='card-theme']")
    expect(theme).to_have_text("none")
    card.evaluate("el => el.setAttribute('theme-color', 'dark')")
    expect(theme).to_have_text("dark")
    card.evaluate("el => el.setAttribute('theme-color', 'light')")
    expect(theme).to_have_text("light")
    card.evaluate("el => el.removeAttribute('theme-color')")
    expect(theme).to_have_text("none")


def test_host_style_and_reactive_host_style(page_on):
    page = page_on("/custom-elements")
    page.wait_for_function("() => getComputedStyle(document.querySelector('e2e-card')).display === 'block'")
    page.wait_for_function("() => getComputedStyle(document.querySelector('e2e-card')).color === 'rgb(0, 0, 255)'")


def test_no_console_errors(page_on):
    page = page_on("/custom-elements")
    expect(page.locator("[data-testid='custom-element-page']")).to_be_visible()
