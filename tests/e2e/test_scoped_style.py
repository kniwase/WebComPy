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


def test_scoped_style_media_query(page_on):
    page = page_on("/scoped-style")
    media_text = page.locator("[data-testid='media-text']")
    expect(media_text).to_be_visible()

    color = media_text.evaluate("el => getComputedStyle(el).color")
    assert color in ("rgb(0, 0, 255)", "blue", "#0000ff"), f"Expected blue color, got {color}"

    style_content = page.locator("style").first.evaluate("el => el.textContent")
    assert "@media" in style_content
    assert "media-text" in style_content
    assert "@media (max-width: 768px) {" in style_content or "@media(max-width:768px){" in style_content.replace(
        " ", ""
    )


def test_scoped_style_pseudo_class_nesting(page_on):
    page = page_on("/scoped-style")
    hover_text = page.locator("[data-testid='hover-text']")
    expect(hover_text).to_be_visible()

    color = hover_text.evaluate("el => getComputedStyle(el).color")
    assert color in ("rgb(128, 0, 128)", "purple", "#800080"), f"Expected purple color, got {color}"

    style_content = page.locator("style").first.evaluate("el => el.textContent")
    assert ":hover" in style_content
    assert "hover-text" in style_content
    assert ":hover {" in style_content or ":hover{" in style_content.replace(" ", "")


def test_scoped_style_deep_nesting(page_on):
    page = page_on("/scoped-style")
    deep_text = page.locator("[data-testid='deep-text']")
    expect(deep_text).to_be_visible()

    color = deep_text.evaluate("el => getComputedStyle(el).color")
    assert color in ("rgb(255, 165, 0)", "orange", "#ffa500"), f"Expected orange color, got {color}"

    style_content = page.locator("style").first.evaluate("el => el.textContent")
    assert "@media" in style_content


def test_scoped_style_combinator_selector(page_on):
    page = page_on("/scoped-style")
    combinator_text = page.locator("[data-testid='combinator-text']")
    expect(combinator_text).to_be_visible()

    color = combinator_text.evaluate("el => getComputedStyle(el).color")
    assert color in ("rgb(0, 0, 128)", "navy", "#000080"), f"Expected navy color, got {color}"

    style_content = page.locator("style").first.evaluate("el => el.textContent")
    assert ">" in style_content


def test_scoped_style_top_level_media_query(page_on):
    page = page_on("/scoped-style")
    top_level_media_text = page.locator("[data-testid='top-level-media-text']")
    expect(top_level_media_text).to_be_visible()

    style_content = page.locator("style").first.evaluate("el => el.textContent")

    assert "@media (max-width:" in style_content or "@media(max-width:" in style_content.replace(" ", "")
    assert "@media[webcompy-cid-" not in style_content

    assert "top-level-media-text" in style_content
    assert "webcompy-cid-" in style_content
