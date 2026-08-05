import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_boundary_catches_crash_and_retry_recovers(page_on):
    page = page_on("/error-boundary")
    expect(page.locator("[data-testid='risky-widget']")).to_be_visible()
    expect(page.locator("[data-testid='eb-sibling']")).to_have_text("alive")

    page.locator("[data-testid='crash-widget']").click()
    expect(page.locator("[data-testid='eb-fallback']")).to_be_visible()
    expect(page.locator("[data-testid='eb-error']")).to_contain_text("widget render failed")
    expect(page.locator("[data-testid='risky-widget']")).to_have_count(0)
    expect(page.locator("[data-testid='eb-sibling']")).to_have_text("alive")

    page.locator("[data-testid='eb-retry']").click()
    expect(page.locator("[data-testid='risky-widget']")).to_be_visible()
    expect(page.locator("[data-testid='eb-fallback']")).to_have_count(0)


def test_page_crash_preserves_layout(page_on):
    page = page_on("/nested/crash")
    expect(page.locator("[data-testid='nested-layout']")).to_be_visible()
    expect(page.locator("[data-testid='nested-crash-page']")).to_be_visible()

    page.locator("[data-testid='crash-page']").click()
    expect(page.locator("[data-testid='nested-crash-page']")).to_have_count(0)
    expect(page.locator("[data-testid='nested-layout']")).to_be_visible()

    page.locator("[data-testid='nested-toggle']").click()
    expect(page.locator("[data-testid='nested-sidebar']")).to_have_text("closed")

    page.locator("[data-testid='nav-nested-guide']").click()
    expect(page).to_have_url(re.compile(r"/nested/guide"))
    expect(page.locator("[data-testid='nested-guide-page']")).to_be_visible()


def test_renavigation_retries_errored_level(page_on):
    page = page_on("/nested/crash")
    expect(page.locator("[data-testid='nested-crash-page']")).to_be_visible()

    page.locator("[data-testid='crash-page']").click()
    expect(page.locator("[data-testid='nested-crash-page']")).to_have_count(0)

    page.locator("[data-testid='nav-nested-crash']").click()
    expect(page.locator("[data-testid='nested-crash-page']")).to_be_visible()
