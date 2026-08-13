import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_last_page_omits_next_link(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/readonly-signal")
    expect(page.locator(".docs-pager-prev")).to_have_count(1)
    expect(page.locator(".docs-pager-prev a")).to_have_text("Signals and Streams")
    expect(page.locator(".docs-pager-next")).to_have_count(0)


@pytest.mark.e2e
def test_readonly_signal_renders_inside_layout(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/readonly-signal")
    assert page.title() == "Read-only Signals and Events - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="Read-only Signals and Events")).to_be_visible()


@pytest.mark.e2e
def test_readonly_signal_toc(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/readonly-signal")
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#usereadonlysignal-an-external-only-write-path"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#usewindowevent-window-state-events"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#usedocumentevent-document-state-events"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#standalone-usage"]')).to_be_visible()
