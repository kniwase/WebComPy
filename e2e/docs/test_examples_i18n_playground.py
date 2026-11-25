import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe

pytestmark = pytest.mark.e2e


def test_examples_i18n_playground_locale_and_plural(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/i18n-playground")
    assert page.title() == "i18n Playground - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text("i18n Playground")
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()

    frame = _wait_for_demo_iframe(page, "i18n_playground")
    expect(frame.locator(".i18n-current")).to_have_text("Current locale: en")
    expect(frame.locator(".i18n-items")).to_have_text("3 items")

    frame.get_by_role("button", name="日本語").click()
    expect(frame.locator(".i18n-current")).to_have_text("現在のロケール: ja")
    expect(frame.locator(".i18n-items")).to_have_text("3 個のアイテム")

    frame.get_by_role("button", name="+").click()
    expect(frame.locator(".i18n-items")).to_have_text("4 個のアイテム")
