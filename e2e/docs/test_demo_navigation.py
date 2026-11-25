import pytest
from playwright.sync_api import expect

HELLOWORLD_MARKER = "HelloWorld"
TODO_MARKER = "TodoApp"


@pytest.mark.e2e
def test_initial_load_restores_code_without_main_frame_refetch(docs_page_on, page):
    requests: list[str] = []

    def _on_request(req):
        if req.frame == page.main_frame and "/_demos/helloworld/app.py" in req.url:
            requests.append(req.url)

    page.on("request", _on_request)
    docs_page_on("/documents/examples/hello-world")
    expect(page.locator(".demo-display-root .code-block")).to_contain_text(HELLOWORLD_MARKER)
    page.wait_for_timeout(1500)
    page.remove_listener("request", _on_request)
    assert not requests, f"code was refetched from the main frame: {requests}"


@pytest.mark.e2e
def test_spa_navigation_updates_code_and_fetches_new_source(docs_page_on, page):
    docs_page_on("/documents/examples/hello-world")
    code_block = page.locator(".demo-display-root .code-block")
    expect(code_block).to_contain_text(HELLOWORLD_MARKER)

    requests: list[str] = []

    def _on_request(req):
        if req.frame == page.main_frame and "/_demos/todo/app.py" in req.url:
            requests.append(req.url)

    page.on("request", _on_request)
    page.locator('.docs-sidebar a[href="/documents/examples/todo/"]').first.click()

    expect(page.locator(".demo-display-title")).to_have_text("ToDo List")
    expect(code_block).to_contain_text(TODO_MARKER)
    page.remove_listener("request", _on_request)
    assert requests, "expected a main-frame fetch of /_demos/todo/app.py after navigation"


@pytest.mark.e2e
def test_removed_sample_route_renders_404(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/todo")
    expect(page.get_by_role("heading", name="404 - Not Found")).to_be_visible()
    expect(page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Demos")).to_have_count(0)
