import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe

pytestmark = pytest.mark.e2e


def test_examples_fetch_middleware_mocks_without_network(page, docs_page_on, assert_no_console_errors):
    api_requests: list[str] = []
    page.on("request", lambda req: api_requests.append(req.url) if "/api/notes" in req.url else None)

    docs_page_on("/documents/examples/fetch-middleware")
    assert page.title() == "Fetch Middleware - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text("Fetch Middleware")
    expect(page.get_by_role("heading", name="Real server wiring")).to_be_visible()
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()

    frame = _wait_for_demo_iframe(page, "fetch_middleware_mock")
    expect(frame.locator(".notes-list")).to_contain_text("Intercept GET /api/notes")
    expect(frame.locator(".trace-list")).to_contain_text("GET /api/notes -> 200")

    frame.get_by_placeholder("New note title...").fill("Static middleware note")
    frame.get_by_role("button", name="Add Note").click()
    expect(frame.locator(".notes-list")).to_contain_text("Static middleware note [custom]")
    expect(frame.locator(".trace-list")).to_contain_text("POST /api/notes -> 201")
    assert api_requests == []
