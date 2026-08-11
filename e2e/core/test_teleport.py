import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_modal_opens_under_body(page_on):
    page = page_on("/teleport")
    expect(page.locator("[data-testid='teleport-modal']")).to_have_count(0)
    page.locator("[data-testid='toggle-modal']").click()
    modal = page.locator("[data-testid='teleport-modal']")
    expect(modal).to_be_visible()
    expect(modal).to_contain_text("modal-content")
    assert (page.evaluate("document.querySelector('[data-testid=\"teleport-modal\"]').parentElement.tagName")) == "BODY"
    expect(page.locator("[data-testid='before-marker']")).to_be_visible()
    expect(page.locator("[data-testid='after-marker']")).to_be_visible()


def test_modal_close_removes_nodes(page_on):
    page = page_on("/teleport")
    page.locator("[data-testid='toggle-modal']").click()
    expect(page.locator("[data-testid='teleport-modal']")).to_be_visible()
    page.locator("[data-testid='toggle-modal']").click()
    expect(page.locator("[data-testid='teleport-modal']")).to_have_count(0)
    assert page.evaluate("document.body.querySelector('[data-testid=\"teleport-modal\"]')") is None


def test_sibling_stability_across_toggle(page_on):
    page = page_on("/teleport")
    for _ in range(3):
        page.locator("[data-testid='toggle-modal']").click()
        expect(page.locator("[data-testid='teleport-modal']")).to_be_visible()
        page.locator("[data-testid='toggle-modal']").click()
        expect(page.locator("[data-testid='teleport-modal']")).to_have_count(0)
    expect(page.locator("[data-testid='before-marker']")).to_have_text("before-marker")
    expect(page.locator("[data-testid='after-marker']")).to_have_text("after-marker")
    expect(page.locator("[data-testid='teleport-page']")).to_be_visible()


def test_ssr_static_teleport_mounts_under_body_without_duplication(page_on):
    page = page_on("/teleport")
    static = page.locator("[data-testid='static-teleport']")
    expect(static).to_have_count(1)
    assert (
        page.evaluate("document.querySelector('[data-testid=\"static-teleport\"]').parentElement.tagName")
    ) == "BODY"
    expect(page.locator("[data-testid='before-marker']")).to_have_count(1)
    expect(page.locator("[data-testid='after-marker']")).to_have_count(1)
    expect(page.locator("[data-testid='after-marker']")).to_have_text("after-marker")
