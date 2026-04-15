import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_scoped_style_applied(page_on):
    page = page_on("/scoped-style")
    expect(page.locator("[data-testid='scoped-style-page']")).to_be_visible()

    styled_text = page.locator("[data-testid='styled-text']")
    expect(styled_text).to_be_visible()

    color = styled_text.evaluate("el => getComputedStyle(el).color")
    assert color in ("rgb(255, 0, 0)", "red", "#ff0000"), f"Expected red color, got {color}"


def test_scoped_style_attribute_selector(page_on):
    page = page_on("/scoped-style")
    style_element = page.locator("style").first
    style_content = style_element.evaluate("el => el.textContent")
    assert "webcompy-cid-" in style_content
