import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_transition_page_loads(page_on):
    page = page_on("/transition")
    expect(page.locator("[data-testid='transition-page']")).to_be_visible()
    expect(page.locator("[data-testid='fade-box']")).to_have_count(0)


def test_transition_fade_enter_and_leave(page_on):
    page = page_on("/transition")
    page.locator("[data-testid='toggle-fade']").click()
    box = page.locator("[data-testid='fade-box']")
    expect(box).to_be_visible()
    expect(box).to_contain_class("fade-enter-active")
    expect(box).not_to_contain_class("fade-enter-active")
    expect(box).to_be_visible()

    page.locator("[data-testid='toggle-fade']").click()
    expect(box).to_be_visible()
    expect(box).to_contain_class("fade-leave-active")
    expect(box).to_have_count(0)


def test_transition_end_event_finalizes_early(page_on):
    page = page_on("/transition")
    page.locator("[data-testid='toggle-fade']").click()
    box = page.locator("[data-testid='fade-box']")
    expect(box).to_contain_class("fade-enter-active")
    page.evaluate(
        """() => {
            const box = document.querySelector("[data-testid='fade-box']");
            box.dispatchEvent(new Event("transitionend", { bubbles: true }));
        }"""
    )
    expect(box).not_to_contain_class("fade-enter-active", timeout=200)
    expect(box).not_to_contain_class("fade-enter-from", timeout=200)
    expect(box).to_be_visible()


def test_transition_teleport_combo(page_on):
    page = page_on("/transition")
    page.locator("[data-testid='toggle-slide']").click()
    box = page.locator("body > .e2e-slide-box")
    expect(box).to_be_visible()
    expect(box).to_contain_class("slide-enter-active")
    expect(box).not_to_contain_class("slide-enter-active")

    page.locator("[data-testid='toggle-slide']").click()
    expect(box).to_be_visible()
    expect(box).to_contain_class("slide-leave-active")
    expect(box).to_have_count(0)
