import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_client_only_fallback_present_on_load(page_on):
    page = page_on("/client-only")
    expect(page.locator("[data-testid='client-only-page']")).to_be_visible()
    expect(page.locator("[data-testid='server-content']")).to_be_visible()
    expect(page.locator("[data-testid='browser-content']")).to_be_visible()
    expect(page.locator("[data-testid='fallback']")).to_have_count(0)


def test_client_only_replaces_fallback(page_on):
    page = page_on("/client-only")
    expect(page.locator("[data-testid='browser-content']")).to_have_text("This is browser-only content")
    expect(page.locator("[data-testid='server-content']")).to_have_text("This is server-rendered")
