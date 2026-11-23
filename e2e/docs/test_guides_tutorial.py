import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe


def _assert_doc_chrome(page, expected_title: str) -> None:
    assert page.title() == f"{expected_title} - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text(expected_title)
    expect(page.locator(".docs-toc a").first).to_be_visible()
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()


@pytest.mark.e2e
def test_guides_overview_page(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/guides/overview")
    _assert_doc_chrome(page, "Guides Overview")
    expect(page.locator(".docs-pager-prev a")).to_have_text("Project Structure")
    expect(page.locator(".docs-pager-next a")).to_have_text("Step 1: App Shell")


@pytest.mark.e2e
def test_guides_step1_state_page(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/guides/todo-app-shell")
    _assert_doc_chrome(page, "Step 1 — App Shell and Reactive State")
    frame = _wait_for_demo_iframe(page, "todo_tutorial/step1")
    expect(frame.locator("h1")).to_have_text("ToDo Tutorial")
    expect(frame.locator("li").filter(has_text="Read Getting Started")).to_be_visible()
    frame.get_by_role("button", name="Active").click()
    expect(frame.locator("li").filter(has_text="Read Getting Started")).not_to_be_visible()
    expect(frame.locator("li").filter(has_text="Build TodoApp state")).to_be_visible()


@pytest.mark.e2e
def test_guides_step2_components_page(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/guides/todo-components")
    _assert_doc_chrome(page, "Step 2 — Components")
    frame = _wait_for_demo_iframe(page, "todo_tutorial/step2")
    expect(frame.locator("todo-toolbar .remaining")).to_have_text("2 remaining")
    expect(frame.locator("li").filter(has_text="Split into components")).to_be_visible()


@pytest.mark.e2e
def test_guides_step3_navigation_page(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/guides/todo-navigation")
    _assert_doc_chrome(page, "Step 3 — Navigation")
    frame = _wait_for_demo_iframe(page, "todo_tutorial/step3")
    expect(frame.locator("li").filter(has_text="Read Getting Started")).to_be_visible()
    frame.get_by_role("link", name="Active").click()
    expect(frame.locator("li").filter(has_text="Read Getting Started")).not_to_be_visible()
    expect(frame.locator("li").filter(has_text="Add client-side routing")).to_be_visible()


@pytest.mark.e2e
def test_guides_step4_forms_page(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/guides/todo-forms")
    _assert_doc_chrome(page, "Step 4 — Forms")
    frame = _wait_for_demo_iframe(page, "todo_tutorial/step4")
    expect(frame.locator("li").filter(has_text="Validate new tasks")).to_be_visible()
    frame.locator("input[placeholder='What needs to be done?']").fill("Review step 4")
    frame.get_by_role("button", name="Add Task").click()
    expect(frame.locator("li").filter(has_text="Review step 4")).to_be_visible()


@pytest.mark.e2e
def test_guides_step5_remote_data_page(page, docs_page_on, assert_no_console_errors):
    api_requests: list[str] = []
    page.on("request", lambda req: api_requests.append(req.url) if "/api/tasks" in req.url else None)
    docs_page_on("/documents/guides/todo-remote-data")
    _assert_doc_chrome(page, "Step 5 — Remote Data")
    frame = _wait_for_demo_iframe(page, "todo_tutorial/step5")
    expect(frame.locator("li").filter(has_text="Connect to /api/tasks")).to_be_visible()
    frame.locator("input[placeholder='What needs to be done?']").fill("Ship static site")
    frame.get_by_role("button", name="Add Task").click()
    expect(frame.locator("li").filter(has_text="Ship static site")).to_be_visible()
    assert api_requests == []


@pytest.mark.e2e
def test_guides_step6_deploy_page(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/guides/todo-deploy")
    _assert_doc_chrome(page, "Step 6 — Deploy")
    expect(page.locator(".docs-pager-prev a")).to_have_text("Step 5: Remote Data")
    expect(page.locator(".docs-pager-next a")).to_have_text("Components")
    frame = _wait_for_demo_iframe(page, "todo_tutorial/step6")
    expect(frame.locator("li").filter(has_text="Prepare for static deploy")).to_be_visible()
