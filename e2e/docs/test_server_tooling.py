import pytest
from playwright.sync_api import expect

_SERVER_TOOLING_PAGES = [
    ("/documents/server/cli-reference", "CLI Reference", "Inspect subcommands"),
    ("/documents/server/project-configuration", "Project Configuration", "WebComPyBuildConfig field reference"),
    ("/documents/server/asgi-integration", "ASGI Integration", "Embedding WebComPy in a FastAPI or Starlette host"),
    ("/documents/server/serving-modes", "Serving Modes", "Offline and firewall deployment checklist"),
    ("/documents/server/testing", "Testing", "Recipe: testing a component that fetches data"),
]


@pytest.mark.e2e
@pytest.mark.parametrize(
    ("path", "title", "toc_heading"),
    _SERVER_TOOLING_PAGES,
    ids=[entry[0].rsplit("/", 1)[-1] for entry in _SERVER_TOOLING_PAGES],
)
def test_server_tooling_page_renders_with_toc_and_code(
    docs_page_on,
    assert_no_console_errors,
    path: str,
    title: str,
    toc_heading: str,
) -> None:
    page = docs_page_on(path)
    assert page.title() == f"{title} - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.locator(".docs-sidebar-active")).to_contain_text(title)
    expect(page.get_by_role("heading", name=title, level=1)).to_be_visible()
    expect(page.get_by_role("heading", name="Next steps", level=2)).to_be_visible()
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator(".docs-toc-list a", has_text=toc_heading)).to_be_visible()
    expect(page.locator("article.prose pre code").first).to_be_visible()


@pytest.mark.e2e
def test_server_tooling_toc_anchor_and_pager_boundaries(docs_page_on, assert_no_console_errors) -> None:
    page = docs_page_on("/documents/server/cli-reference")
    expect(page.locator(".docs-pager-prev a")).to_have_text("Internationalization")
    expect(page.locator(".docs-pager-next a")).to_have_text("Project Configuration")

    toc_link = page.locator('.docs-toc a[href$="#worked-examples"]')
    expect(toc_link).to_be_visible()
    toc_link.click()
    assert page.url.endswith("#worked-examples")

    page = docs_page_on("/documents/server/testing")
    expect(page.locator(".docs-pager-prev a")).to_have_text("Serving Modes")
    expect(page.locator(".docs-pager-next")).to_have_count(0)
