import pytest


@pytest.mark.e2e
def test_todo_initial_items(docs_page_on, assert_no_python_errors):
    page = docs_page_on("/sample/todo")
    assert page.locator("span").filter(has_text="Try WebComPy").first.is_visible()
    assert page.locator("span").filter(has_text="Create WebComPy project").first.is_visible()


@pytest.mark.e2e
def test_todo_add_item(docs_page_on, assert_no_python_errors):
    page = docs_page_on("/sample/todo")
    input_field = page.locator("p").locator("input").first
    input_field.fill("Test item")
    page.get_by_role("button", name="Add ToDo").click()
    assert page.locator("li").filter(has_text="Test item").is_visible()


@pytest.mark.e2e
def test_todo_remove_done_items(docs_page_on, assert_no_python_errors):
    page = docs_page_on("/sample/todo")
    checkboxes = page.locator("input[type='checkbox']")
    checkboxes.first.check()
    page.get_by_role("button", name="Remove Done Items").click()
    assert not page.locator("li").filter(has_text="Try WebComPy").is_visible()
