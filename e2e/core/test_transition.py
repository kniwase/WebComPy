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


def test_component_wrapper_default_display_is_contents(page_on):
    page = page_on("/transition")
    page.locator("[data-testid='toggle-comp']").click()
    page.wait_for_function(
        "() => { const el = document.querySelector('[data-testid=\"comp-box\"]');"
        " return el && getComputedStyle(el.parentElement).display === 'contents'; }"
    )


def test_component_wrapper_display_kwarg_is_block(page_on):
    page = page_on("/transition")
    page.locator("[data-testid='toggle-block']").click()
    page.wait_for_function(
        "() => { const el = document.querySelector('[data-testid=\"block-box\"]');"
        " return el && getComputedStyle(el.parentElement).display === 'block'; }"
    )


def test_layout_transparent_component_child_warns_and_finalizes_via_timeout(page_on):
    page = page_on("/transition")
    messages: list[str] = []
    page.on("console", lambda msg: messages.append(msg.text))
    page.locator("[data-testid='toggle-comp']").click()
    box = page.locator("[data-testid='comp-box']")
    expect(box).to_be_visible()
    page.locator("[data-testid='toggle-comp']").click()
    expect(box).to_have_count(0, timeout=3000)
    assert any("display" in message and "contents" in message for message in messages), (
        "layout-transparent component child must trigger the Transition display warning"
    )


def test_box_generating_component_child_animates_without_warning(page_on):
    page = page_on("/transition")
    messages: list[str] = []
    page.on("console", lambda msg: messages.append(msg.text))
    page.locator("[data-testid='toggle-block']").click()
    box = page.locator("[data-testid='block-box']")
    wrapper = page.locator("block-box")
    expect(box).to_be_visible()
    expect(wrapper).to_contain_class("fade-enter-active")
    expect(wrapper).not_to_contain_class("fade-enter-active")
    expect(box).to_be_visible()

    page.locator("[data-testid='toggle-block']").click()
    expect(wrapper).to_contain_class("fade-leave-active")
    expect(box).to_have_count(0, timeout=3000)
    assert not any("display" in message and "contents" in message for message in messages), (
        "box-generating component child must not trigger the Transition display warning"
    )
