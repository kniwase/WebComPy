import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe

pytestmark = pytest.mark.e2e


def test_examples_routing_nested_layout_and_guard(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/routing")
    assert page.title() == "Routing - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text("Routing")
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()

    frame = _wait_for_demo_iframe(page, "routing")
    expect(frame.get_by_role("heading", name="Home View")).to_be_visible()

    frame.locator(".top-nav").get_by_role("link", name="Workspace").click()
    expect(frame.get_by_role("heading", name="Workspace Overview")).to_be_visible()
    expect(frame.locator(".sidebar-status")).to_have_text("Sidebar: expanded")

    frame.get_by_role("button", name="Toggle Sidebar").click()
    expect(frame.locator(".sidebar-status")).to_have_text("Sidebar: compact")

    frame.get_by_role("link", name="Settings").click()
    expect(frame.get_by_role("heading", name="Workspace Settings")).to_be_visible()
    expect(frame.locator(".sidebar-status")).to_have_text("Sidebar: compact")

    frame.get_by_role("link", name="Item 42").click()
    expect(frame.get_by_role("heading", name="Workspace Item #42")).to_be_visible()
    expect(frame.locator(".sidebar-status")).to_have_text("Sidebar: compact")

    frame.locator(".top-nav").get_by_role("link", name="Admin").click()
    expect(frame.get_by_role("heading", name="Sign In")).to_be_visible()
    expect(frame.locator(".guard-notice")).to_contain_text("Redirected from /admin")

    frame.get_by_role("button", name="Sign in as Admin").click()
    expect(frame.get_by_role("heading", name="Protected Admin")).to_be_visible()
