import pytest
from playwright.sync_api import expect

_API_REFERENCE_PAGES = [
    ("/documents/api/app-and-components", "App & Components", "App & Components API", "Application & Configuration"),
    (
        "/documents/api/template-and-markdown",
        "Template & Markdown",
        "Template & Markdown API",
        "Template Rendering & AST",
    ),
    ("/documents/api/reactivity", "Reactivity", "Reactivity API", "Signals, Computed & Collections"),
    (
        "/documents/api/elements-and-routing",
        "Elements, Routing & DI",
        "Elements, Routing & DI API",
        "Elements, Control Flow & Head",
    ),
    ("/documents/api/data", "Data, Forms & i18n", "Data, Forms & i18n API", "HTTP, Async & Resources"),
    ("/documents/api/ui", "UI & Theme", "UI & Theme API", "Themed Components"),
    ("/documents/api/server-and-cli", "Server, CLI, RPC & Ports", "Server, CLI, RPC & Ports API", "Typed RPC"),
    ("/documents/api/testing", "Testing", "Testing API", "Browser Test Runner"),
]


@pytest.mark.e2e
@pytest.mark.parametrize(
    ("path", "label", "title", "toc_heading"),
    _API_REFERENCE_PAGES,
    ids=[entry[0].rsplit("/", 1)[-1] for entry in _API_REFERENCE_PAGES],
)
def test_api_reference_page_renders_with_toc_and_signatures(
    docs_page_on,
    assert_no_console_errors,
    path: str,
    label: str,
    title: str,
    toc_heading: str,
) -> None:
    page = docs_page_on(path)
    assert page.title() == f"{title} - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.locator(".docs-sidebar-active")).to_contain_text(label)
    expect(page.get_by_role("heading", name=title, level=1)).to_be_visible()
    expect(page.get_by_role("heading", name="Next steps", level=2)).to_be_visible()
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator(".docs-toc-list a", has_text=toc_heading).first).to_be_visible()
    expect(page.locator("article.prose pre code").first).to_be_visible()


@pytest.mark.e2e
def test_api_reference_toc_anchor_and_pager_boundaries(docs_page_on, assert_no_console_errors) -> None:
    page = docs_page_on("/documents/api/app-and-components")
    expect(page.locator(".docs-pager-prev a")).to_have_text("RPC Middleware")
    expect(page.locator(".docs-pager-next a")).to_have_text("Template & Markdown")

    toc_link = page.locator(".docs-toc a", has_text="Components & Lifecycle").first
    expect(toc_link).to_be_visible()
    href = toc_link.get_attribute("href")
    assert href is not None and "#" in href
    toc_link.click()
    assert page.url.endswith(href)

    page = docs_page_on("/documents/api/testing")
    expect(page.locator(".docs-pager-prev a")).to_have_text("Server, CLI, RPC & Ports")
    expect(page.locator(".docs-pager-next a")).to_have_count(0)
