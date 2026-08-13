import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe


@pytest.mark.e2e
def test_transition_page_loads(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/transition")
    expect(page.locator("h1.page-title")).to_have_text("Transition")


@pytest.mark.e2e
def test_transition_demo_fade(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/transition")
    frame = _wait_for_demo_iframe(page, "transition")
    frame.locator("#toggle-fade").click()
    box = frame.locator(".demo-fade-box")
    expect(box).to_be_visible()
    expect(box).to_contain_class("fade-enter-active")
    expect(box).not_to_contain_class("fade-enter-active")

    frame.locator("#toggle-fade").click()
    expect(box).to_be_visible()
    expect(box).to_contain_class("fade-leave-active")
    expect(box).to_have_count(0)


@pytest.mark.e2e
def test_transition_demo_slide(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/transition")
    frame = _wait_for_demo_iframe(page, "transition")
    frame.locator("#toggle-slide").click()
    box = frame.locator(".demo-slide-box")
    expect(box).to_be_visible()
    expect(box).to_contain_class("slide-enter-active")
    expect(box).not_to_contain_class("slide-enter-active")

    frame.locator("#toggle-slide").click()
    expect(box).to_be_visible()
    expect(box).to_have_count(0)
