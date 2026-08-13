import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_window_resize_updates_signal_from_real_event(page_on):
    page = page_on("/window-events")
    expect(page.locator("[data-testid='window-events-page']")).to_be_visible()

    expect(page.locator("[data-testid='window-width']")).to_have_text("0")

    page.set_viewport_size({"width": 640, "height": 480})
    inner_width = page.evaluate("window.innerWidth")
    expect(page.locator("[data-testid='window-width']")).to_have_text(str(inner_width))

    page.set_viewport_size({"width": 1024, "height": 768})
    inner_width = page.evaluate("window.innerWidth")
    expect(page.locator("[data-testid='window-width']")).to_have_text(str(inner_width))


def test_document_visibilitychange_updates_signal_from_real_event(page_on):
    page = page_on("/window-events")
    expect(page.locator("[data-testid='window-events-page']")).to_be_visible()

    expect(page.locator("[data-testid='document-hidden']")).to_have_text("True")

    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    expect(page.locator("[data-testid='document-hidden']")).to_have_text("False")
