import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe, _wait_for_pyscript_init


@pytest.mark.e2e
def test_examples_hello_world_renders(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/hello-world")
    assert page.title() == "Hello World - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text("Hello World")
    expect(page.locator(".docs-toc a").first).to_be_visible()
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()
    expect(page.locator(".demo-display-root .code-block")).to_contain_text("HelloWorld")

    frame = _wait_for_demo_iframe(page, "helloworld")
    expect(frame.get_by_role("heading", name="Hello WebComPy!")).to_be_visible()


@pytest.mark.e2e
def test_examples_hello_world_reload_no_error(docs_page_on, docs_console_messages, assert_no_console_errors):
    page = docs_page_on("/documents/examples/hello-world")
    page.reload()
    _wait_for_pyscript_init(page, docs_console_messages)
