import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_i18n_guide_renders(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/i18n")
    assert page.title() == "Internationalization - WebComPy Docs"
    expect(page.get_by_role("heading", name="Internationalization")).to_be_visible()


@pytest.mark.e2e
def test_i18n_demo_locale_switch(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/i18n")
    container = page.locator(".page-container")
    expect(page.get_by_role("heading", name="Internationalization (i18n)")).to_be_visible()
    expect(container).to_contain_text("Current locale: en")
    expect(container).to_contain_text("3 items")
    page.get_by_role("button", name="日本語").click()
    expect(container).to_contain_text("現在のロケール: ja")
    expect(container).to_contain_text("3 個のアイテム")
