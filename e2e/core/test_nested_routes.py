import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_nested_layout_renders_layout_and_leaf(page_on):
    page = page_on("/nested/guide")
    expect(page.locator("[data-testid='nested-layout']")).to_be_visible()
    expect(page.locator("[data-testid='nested-guide-page']")).to_be_visible()
    expect(page.locator("[data-testid='nested-api-page']")).to_have_count(0)


def test_nested_index_route(page_on):
    page = page_on("/nested")
    expect(page.locator("[data-testid='nested-layout']")).to_be_visible()
    expect(page.locator("[data-testid='nested-index-page']")).to_be_visible()


def test_sibling_navigation_preserves_layout_state(page_on):
    page = page_on("/nested/guide")
    expect(page.locator("[data-testid='nested-sidebar']")).to_have_text("open")

    page.locator("[data-testid='nested-toggle']").click()
    expect(page.locator("[data-testid='nested-sidebar']")).to_have_text("closed")

    page.locator("[data-testid='nav-nested-api']").click()
    expect(page).to_have_url(re.compile(r"/nested/api"))
    expect(page.locator("[data-testid='nested-api-page']")).to_be_visible()
    expect(page.locator("[data-testid='nested-sidebar']")).to_have_text("closed")

    page.locator("[data-testid='nav-nested-guide']").click()
    expect(page).to_have_url(re.compile(r"/nested/guide"))
    expect(page.locator("[data-testid='nested-guide-page']")).to_be_visible()
    expect(page.locator("[data-testid='nested-sidebar']")).to_have_text("closed")


def test_sibling_navigation_remounts_leaf(page_on):
    page = page_on("/nested/guide")
    expect(page.locator("[data-testid='nested-guide-page']")).to_be_visible()
    guide_count = int(page.locator("[data-testid='nested-guide-count']").text_content())

    page.locator("[data-testid='nav-nested-api']").click()
    expect(page.locator("[data-testid='nested-api-page']")).to_be_visible()
    api_count = int(page.locator("[data-testid='nested-api-count']").text_content())

    page.locator("[data-testid='nav-nested-guide']").click()
    expect(page.locator("[data-testid='nested-guide-page']")).to_be_visible()
    assert int(page.locator("[data-testid='nested-guide-count']").text_content()) == guide_count + 1
    expect(page.locator("[data-testid='nested-api-page']")).to_have_count(0)
    assert api_count > 0


def test_param_change_remounts_leaf(page_on):
    page = page_on("/nested/item/1")
    expect(page.locator("[data-testid='nested-item-page']")).to_be_visible()
    expect(page.locator("[data-testid='nested-item-id']")).to_have_text("1")
    item_count = int(page.locator("[data-testid='nested-item-count']").text_content())

    page.locator("[data-testid='nav-nested-item2']").click()
    expect(page).to_have_url(re.compile(r"/nested/item/2"))
    expect(page.locator("[data-testid='nested-item-id']")).to_have_text("2")
    assert int(page.locator("[data-testid='nested-item-count']").text_content()) == item_count + 1


def test_nested_route_with_query_params(page_on):
    page = page_on("/nested/guide?tab=b")
    expect(page.locator("[data-testid='nested-layout']")).to_be_visible()
    expect(page.locator("[data-testid='nested-guide-page']")).to_be_visible()


def test_query_change_transition_creates_leaf_once(page_on):
    page = page_on("/nested/guide?tab=a")
    expect(page.locator("[data-testid='nested-guide-page']")).to_be_visible()
    guide_count = int(page.locator("[data-testid='nested-guide-count']").text_content())

    page.locator("[data-testid='nav-guide-tab-b']").click()
    expect(page).to_have_url(re.compile(r"/nested/guide/?\?tab=b"))
    expect(page.locator("[data-testid='nested-guide-page']")).to_be_visible()
    assert int(page.locator("[data-testid='nested-guide-count']").text_content()) == guide_count + 1
