import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe

pytestmark = pytest.mark.e2e


def test_examples_transition_page_loads(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/transition")
    assert page.title() == "Transition - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text("Transition")
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()


def test_examples_transition_demo_fade(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/transition")
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


def test_examples_transition_demo_slide(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/transition")
    frame = _wait_for_demo_iframe(page, "transition")
    frame.locator("#toggle-slide").click()
    box = frame.locator(".demo-slide-box")
    expect(box).to_be_visible()
    expect(box).to_contain_class("slide-enter-active")
    expect(box).not_to_contain_class("slide-enter-active")

    frame.locator("#toggle-slide").click()
    expect(box).to_be_visible()
    expect(box).to_have_count(0)
