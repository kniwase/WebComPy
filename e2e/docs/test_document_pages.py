import re

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_documents_index_shows_section_cards(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents")
    expect(page.get_by_role("heading", name="Documentation")).to_be_visible()
    expect(page.get_by_role("heading", name="Getting Started")).to_be_visible()
    expect(page.get_by_role("link", name="Open Installation")).to_be_visible()
    expect(page.get_by_role("link", name="Open Signal Stream")).to_be_visible()


@pytest.mark.e2e
def test_installation_page_title(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/installation")
    assert page.title() == "Installation - WebComPy Docs"


@pytest.mark.e2e
def test_quickstart_page_title(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/quickstart")
    assert page.title() == "Quickstart - WebComPy Docs"


@pytest.mark.e2e
def test_sidebar_visible_and_active_state(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/installation")
    expect(page.locator(".docs-sidebar")).to_be_visible()
    active = page.locator(".docs-sidebar a[aria-current='page']")
    expect(active).to_have_text("Installation")


@pytest.mark.e2e
def test_toc_anchor_navigation(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/installation/")
    toc_link = page.locator(".docs-toc a").first
    expect(toc_link).to_be_visible()
    href = toc_link.get_attribute("href")
    assert href.startswith("/documents/getting-started/installation/#")
    target_id = href.rsplit("#", 1)[-1]
    page.evaluate("window.__e2e_marker = 1")
    toc_link.click()
    expect(page).to_have_url(re.compile(r"/documents/getting-started/installation/#"))
    expect(page.locator(f"[id='{target_id}']")).to_be_in_viewport()
    assert page.evaluate("window.__e2e_marker") == 1


@pytest.mark.e2e
def test_markdown_content_rendered_with_ids_and_code(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/installation")
    expect(page.locator("article.prose h1#installation")).to_be_visible()
    expect(page.locator("article.prose h2#install-with-uv-recommended")).to_be_visible()
    expect(page.locator("article.prose pre.code-block")).to_have_count(6)
    expect(page.locator("article.prose pre.code-block code.language-bash")).to_have_count(4)
    expect(page.locator("article.prose pre.code-block code.language-python")).to_have_count(1)
    expect(page.locator("article.prose pre.code-block code.language-toml")).to_have_count(1)


@pytest.mark.e2e
def test_first_page_omits_prev_link(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/installation")
    expect(page.locator(".docs-pager-prev")).to_have_count(0)
    expect(page.locator(".docs-pager-next")).to_have_count(1)
    expect(page.locator(".docs-pager-next a")).to_have_text("Quickstart")


@pytest.mark.e2e
def test_middle_page_shows_both_links(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/quickstart")
    expect(page.locator(".docs-pager-prev a")).to_have_text("Installation")
    expect(page.locator(".docs-pager-next a")).to_have_text("Signal Stream")


@pytest.mark.e2e
def test_last_page_omits_next_link(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/signal-stream")
    expect(page.locator(".docs-pager-prev")).to_have_count(1)
    expect(page.locator(".docs-pager-prev a")).to_have_text("Quickstart")
    expect(page.locator(".docs-pager-next")).to_have_count(0)


@pytest.mark.e2e
def test_next_navigation_updates_sidebar_active(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/quickstart")
    page.locator(".docs-pager-next a").click()
    expect(page).to_have_url(re.compile(r"/documents/signal-stream"))
    expect(page.get_by_role("heading", name="Signals and Streams")).to_be_visible()
    expect(page.locator(".docs-sidebar a[aria-current='page']")).to_have_text("Signal Stream")


@pytest.mark.e2e
def test_signal_stream_renders_inside_layout(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/signal-stream")
    assert page.title() == "Signal Stream - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.get_by_role("heading", name="Signals and Streams")).to_be_visible()


@pytest.mark.e2e
def test_mobile_sidebar_toggle_and_close_after_navigation(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/installation")
    page.set_viewport_size({"width": 600, "height": 800})
    toggle = page.locator(".docs-sidebar-toggle")
    expect(toggle).to_be_visible()
    expect(page.locator(".docs-sidebar")).to_have_class("docs-sidebar")
    toggle.click()
    expect(page.locator(".docs-sidebar")).to_have_class("docs-sidebar open")
    page.locator(".docs-sidebar a[href*='quickstart']").click()
    expect(page).to_have_url(re.compile(r"/documents/getting-started/quickstart"))
    expect(page.locator(".docs-sidebar")).to_have_class("docs-sidebar")
