import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_markdown_for_initial_render(page_on):
    page = page_on("/markdown-for")
    expect(page.locator("[data-testid='markdown-for-page']")).to_be_visible()
    ul = page.locator("[data-testid='markdown-for-page'] ul")
    expect(ul).to_have_count(1)
    lis = ul.locator("li")
    expect(lis).to_have_count(2)
    expect(lis.nth(0)).to_contain_text("alpha")
    expect(lis.nth(1)).to_contain_text("beta")


def test_markdown_for_collection_append_after_hydration(page_on):
    page = page_on("/markdown-for")
    ul = page.locator("[data-testid='markdown-for-page'] ul")
    lis = ul.locator("li")
    expect(lis).to_have_count(2)

    page.locator("[data-testid='add-item']").click()

    expect(lis).to_have_count(3)
    expect(lis.nth(2)).to_contain_text("gamma")
