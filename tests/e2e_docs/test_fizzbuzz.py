import pytest


@pytest.mark.e2e
def test_fizzbuzz_initial_state(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/fizzbuzz")
    assert page.get_by_text("Count: 10").is_visible()


@pytest.mark.e2e
def test_fizzbuzz_add_button(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/fizzbuzz")
    add_button = page.get_by_role("button", name="Add")
    add_button.click()
    assert page.get_by_text("Count: 11").is_visible()


@pytest.mark.e2e
def test_fizzbuzz_pop_button(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/fizzbuzz")
    pop_button = page.get_by_role("button", name="Pop")
    pop_button.click()
    assert page.get_by_text("Count: 9").is_visible()


@pytest.mark.e2e
def test_fizzbuzz_hide_toggle(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/fizzbuzz")
    toggle_button = page.get_by_role("button", name="Hide")
    toggle_button.click()
    assert page.locator("div").filter(has_text="FizzBuzz Hidden").first.is_visible()
    show_button = page.get_by_role("button", name="Open")
    assert show_button.is_visible()
