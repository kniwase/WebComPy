import pytest
from playwright.sync_api import expect

_RENDERING_PAGES = [
    ("/documents/advanced/ssr-and-ssg", "SSR & SSG", "The dual-environment pipeline"),
    (
        "/documents/advanced/hydration-and-transfer",
        "Hydration & Data Transfer",
        "Payload lifecycle and initial-window gating",
    ),
    (
        "/documents/advanced/async-rendering-and-boundaries",
        "Async Rendering & Boundaries",
        "Coordinating async trees with Suspense",
    ),
    ("/documents/advanced/transition", "Transition", "Enter and leave class protocol"),
    ("/documents/advanced/teleport", "Teleport", "SSR block emission and hydration"),
    ("/documents/advanced/loading-screen", "Loading Screen", "Presentation modes and configuration"),
    ("/documents/advanced/styling-deep-dive", "Styling Deep Dive", "The full CSS @layer cascade model"),
]


@pytest.mark.e2e
@pytest.mark.parametrize(("path", "title", "toc_heading"), _RENDERING_PAGES)
def test_advanced_rendering_page_renders_with_toc(
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
def test_advanced_sidebar_shows_group_headers_on_wide_viewport(docs_page_on, assert_no_console_errors) -> None:
    page = docs_page_on("/documents/advanced/ssr-and-ssg")
    page.set_viewport_size({"width": 1280, "height": 900})
    groups = page.locator(".docs-sidebar-group")
    expect(groups).to_have_count(3)
    expect(groups.nth(0)).to_be_visible()
    expect(groups.nth(0)).to_have_text("Realtime & RPC")
    expect(groups.nth(1)).to_be_visible()
    expect(groups.nth(1)).to_have_text("Rendering & Performance")
    expect(groups.nth(2)).to_be_visible()
    expect(groups.nth(2)).to_have_text("Architecture & Integration")


@pytest.mark.e2e
def test_pager_walks_across_group_boundaries(docs_page_on, assert_no_console_errors) -> None:
    page = docs_page_on("/documents/advanced/ssr-and-ssg")
    expect(page.locator(".docs-pager-prev a")).to_have_text("RPC Streaming")
    expect(page.locator(".docs-pager-next a")).to_have_text("Hydration & Data Transfer")

    page = docs_page_on("/documents/advanced/styling-deep-dive")
    expect(page.locator(".docs-pager-prev a")).to_have_text("Loading Screen")
    expect(page.locator(".docs-pager-next a")).to_have_text("Progressive Web App")

    page = docs_page_on("/documents/advanced/i18n")
    expect(page.locator(".docs-pager-prev a")).to_have_text("Persistence Patterns")
    expect(page.locator(".docs-pager-next")).to_have_count(0)
