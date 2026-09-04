import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_next_link_points_to_readonly_signal(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/signal-stream")
    expect(page.locator(".docs-pager-prev")).to_have_count(1)
    expect(page.locator(".docs-pager-prev a")).to_have_text("Custom Elements")
    expect(page.locator(".docs-pager-next")).to_have_count(1)
    expect(page.locator(".docs-pager-next a")).to_have_text("Read-only Signals and Events")


@pytest.mark.e2e
def test_signal_stream_renders_inside_layout(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/signal-stream")
    assert page.title() == "Signals and Streams - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="Signals and Streams")).to_be_visible()


@pytest.mark.e2e
def test_signal_stream_toc(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/advanced/signal-stream")
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#tosignal-one-shot-values"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#toreactivelist-accumulating-feeds"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#toasynciter-consuming-signal-updates"]')).to_be_visible()
    expect(page.locator('.docs-toc a[href$="#queue-policy-and-lifecycle"]')).to_be_visible()
