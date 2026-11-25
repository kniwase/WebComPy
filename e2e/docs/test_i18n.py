import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_i18n_guide_renders(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/i18n")
    assert page.title() == "Internationalization - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="Internationalization", level=1)).to_be_visible()
    expect(page.get_by_role("heading", name="Deterministic SSR and hydration parity", level=2)).to_be_visible()
    expect(page.get_by_role("heading", name="Late client-side locale mutation breaks parity", level=3)).to_be_visible()
    expect(page.get_by_role("heading", name="Next steps", level=2)).to_be_visible()
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#setup"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#deterministic-ssr-and-hydration-parity"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#late-client-side-locale-mutation-breaks-parity"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#next-steps"]')).to_be_visible()
    expect(page.locator(".docs-pager-prev a")).to_have_text("Persistence Patterns")
    expect(page.locator(".docs-pager-next a")).to_have_text("CLI Reference")
