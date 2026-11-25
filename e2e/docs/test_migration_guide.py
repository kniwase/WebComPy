import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe

pytestmark = pytest.mark.e2e


def test_migration_from_jinja2_fastapi_page_and_demo(page, docs_page_on, assert_no_console_errors) -> None:
    api_requests: list[str] = []
    page.on("request", lambda req: api_requests.append(req.url) if "/api/users" in req.url else None)

    docs_page_on("/documents/migration/from-jinja2-fastapi")
    assert page.title() == "Migrating from Jinja2 + FastAPI - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.locator(".docs-sidebar-active")).to_contain_text("From Jinja2 + FastAPI")
    expect(page.get_by_role("heading", name="Migrating from Jinja2 + FastAPI", level=1)).to_be_visible()
    expect(page.get_by_role("heading", name="Choosing an integration strategy", level=2)).to_be_visible()
    expect(page.get_by_role("heading", name="Phased strangler checklist", level=2)).to_be_visible()
    expect(page.get_by_role("heading", name="Next steps", level=2)).to_be_visible()
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator(".docs-pager-prev a")).to_have_text("RPC Middleware")
    expect(page.locator(".docs-pager-next a")).to_have_text("Compatibility Notes")

    toc_link = page.locator(".docs-toc a", has_text="Phased strangler checklist").first
    expect(toc_link).to_be_visible()
    href = toc_link.get_attribute("href")
    assert href is not None and "#" in href
    toc_link.click()
    assert page.url.endswith(href)

    frame = _wait_for_demo_iframe(page, "migration_users")
    expect(frame.locator(".user-summary")).to_have_text("Showing 6 of 6 users")
    expect(frame.locator(".user-list .user-item")).to_have_count(6)
    expect(frame.locator(".user-list")).to_contain_text("Alice Chen")

    search_input = frame.get_by_placeholder("Filter by name or email...")
    search_input.fill("Alice")
    expect(frame.locator(".user-summary")).to_have_text("Showing 1 of 6 users")
    expect(frame.locator(".user-list .user-item")).to_have_count(1)
    expect(frame.locator(".user-list")).to_contain_text("Alice Chen")

    search_input.fill("zzz-no-match")
    expect(frame.locator(".user-summary")).to_have_text("Showing 0 of 6 users")
    expect(frame.locator(".empty-state")).to_have_text("No matching users.")

    frame.get_by_role("button", name="Clear").click()
    expect(frame.locator(".user-summary")).to_have_text("Showing 6 of 6 users")

    frame.get_by_role("button", name="Admin").click()
    expect(frame.locator(".user-summary")).to_have_text("Showing 2 of 6 users")
    expect(frame.locator(".user-list")).to_contain_text("Elena Novak")
    assert api_requests == []


def test_migration_compatibility_notes_page(docs_page_on, assert_no_console_errors) -> None:
    page = docs_page_on("/documents/migration/compatibility-notes")
    assert page.title() == "Jinja2 Compatibility Notes - WebComPy Docs"
    expect(page.locator(".docs-sidebar")).to_be_visible()
    expect(page.locator(".docs-sidebar-active")).to_contain_text("Compatibility Notes")
    expect(page.get_by_role("heading", name="Jinja2 Compatibility Notes", level=1)).to_be_visible()
    expect(page.get_by_role("heading", name="Rejected directives and exact errors", level=2)).to_be_visible()
    expect(page.get_by_role("heading", name="Next steps", level=2)).to_be_visible()
    expect(page.locator(".docs-toc")).to_be_visible()
    expect(page.locator("article.prose")).to_contain_text("{% extends %} is not supported in WebComPy templates")
    expect(page.locator(".docs-pager-prev a")).to_have_text("From Jinja2 + FastAPI")
    expect(page.locator(".docs-pager-next a")).to_have_text("App & Components")


def test_home_migration_card_navigates_to_guide(docs_app_page, assert_no_console_errors) -> None:
    expect(docs_app_page.get_by_text("Coming from Jinja2 + FastAPI?")).to_be_visible()
    docs_app_page.evaluate("window.__home_spa_marker = 1")
    docs_app_page.get_by_role("link", name="Read the Migration Guide →").click()
    assert "/documents/migration/from-jinja2-fastapi" in docs_app_page.url
    expect(docs_app_page.get_by_role("heading", name="Migrating from Jinja2 + FastAPI", level=1)).to_be_visible()
    assert docs_app_page.evaluate("window.__home_spa_marker") == 1
