import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe, _wait_for_pyscript_init


@pytest.mark.e2e
def test_todo_initial_items(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/todo")
    frame = _wait_for_demo_iframe(page, "todo")
    assert frame.locator("span").filter(has_text="Try WebComPy").first.is_visible()
    assert frame.locator("span").filter(has_text="Create WebComPy project").first.is_visible()


@pytest.mark.e2e
def test_todo_add_item(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/todo")
    frame = _wait_for_demo_iframe(page, "todo")
    input_field = frame.locator("p").locator("input").first
    input_field.fill("Test item")
    frame.get_by_role("button", name="Add ToDo").click()
    expect(frame.locator("li").filter(has_text="Test item")).to_be_visible()


@pytest.mark.e2e
def test_todo_remove_done_items(docs_page_on, page, assert_no_console_errors):
    page_errors: list[object] = []
    page.on("pageerror", lambda err: page_errors.append(err))
    page = docs_page_on("/sample/todo")
    frame = _wait_for_demo_iframe(page, "todo")
    checkboxes = frame.locator("input[type='checkbox']")
    checkboxes.first.check()
    frame.get_by_role("button", name="Remove Done Items").click()
    expect(frame.locator("li").filter(has_text="Try WebComPy")).not_to_be_visible()
    assert page_errors == []


@pytest.mark.e2e
def test_todo_reload_no_error(docs_page_on, docs_console_messages, assert_no_console_errors):
    page = docs_page_on("/sample/todo")
    page.reload()
    _wait_for_pyscript_init(page, docs_console_messages)
