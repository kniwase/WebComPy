import re

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_quickstart_page_title(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/quickstart")
    assert page.title() == "Quickstart - WebComPy Docs"


@pytest.mark.e2e
def test_middle_page_shows_both_links(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/quickstart")
    expect(page.locator(".docs-pager-prev a")).to_have_text("Installation")
    expect(page.locator(".docs-pager-next a")).to_have_text("Signal Stream")


@pytest.mark.e2e
def test_next_navigation_updates_sidebar_active(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/quickstart")
    page.locator(".docs-pager-next a").click()
    expect(page).to_have_url(re.compile(r"/documents/signal-stream"))
    expect(page.get_by_role("heading", name="Signals and Streams")).to_be_visible()
    expect(page.locator(".docs-sidebar a[aria-current='page']")).to_have_text("Signal Stream")
