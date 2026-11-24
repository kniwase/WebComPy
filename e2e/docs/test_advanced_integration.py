import pytest
from playwright.sync_api import expect

_INTEGRATION_PAGES = [
    ("/documents/advanced/dependency-injection-deep-dive", "Dependency Injection Deep Dive", "Setup"),
    ("/documents/advanced/middleware", "Middleware", "Recipes"),
    ("/documents/advanced/routing-deep-dive", "Routing Deep Dive", "Behavior notes"),
    ("/documents/advanced/plugins", "Plugins", "Setup"),
    ("/documents/advanced/typed-api-deep-dive", "Typed API Deep Dive", "Recipes"),
    ("/documents/advanced/ui-headless-contract", "UI Headless Contract", "Data-state vocabulary and part-class hooks"),
    ("/documents/advanced/custom-elements", "Custom Elements", "Behavior notes"),
    ("/documents/advanced/persistence-patterns", "Persistence Patterns", "Choosing a persistence mechanism"),
]


@pytest.mark.e2e
@pytest.mark.parametrize(("path", "title", "toc_heading"), _INTEGRATION_PAGES)
def test_advanced_integration_page_renders_with_toc(
    docs_page_on,
    assert_no_console_errors,
    path: str,
    title: str,
    toc_heading: str,
) -> None:
    page = docs_page_on(path)
    assert page.title() == f"{title} - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name=title, level=1)).to_be_visible()
    expect(page.get_by_role("heading", name="Next steps", level=2)).to_be_visible()
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator(".docs-toc-list a", has_text=toc_heading)).to_be_visible()


@pytest.mark.e2e
def test_advanced_integration_sidebar_group_header(docs_page_on, assert_no_console_errors) -> None:
    page = docs_page_on("/documents/advanced/dependency-injection-deep-dive")
    page.set_viewport_size({"width": 1280, "height": 900})
    groups = page.locator(".docs-sidebar-group")
    expect(groups).to_have_count(3)
    expect(groups.nth(2)).to_be_visible()
    expect(groups.nth(2)).to_have_text("Architecture & Integration")


@pytest.mark.e2e
def test_advanced_integration_pager_boundaries(docs_page_on, assert_no_console_errors) -> None:
    page = docs_page_on("/documents/advanced/dependency-injection-deep-dive")
    expect(page.locator(".docs-pager-prev a")).to_have_text("Progressive Web App")
    expect(page.locator(".docs-pager-next a")).to_have_text("Middleware")

    page = docs_page_on("/documents/advanced/persistence-patterns")
    expect(page.locator(".docs-pager-prev a")).to_have_text("Custom Elements")
    expect(page.locator(".docs-pager-next a")).to_have_text("Internationalization")
