import pytest
from playwright.sync_api import expect

from e2e.core.conftest import _wait_for_pyscript_init

pytestmark = pytest.mark.e2e


def test_local_storage_persists_across_reload(page_on, console_messages):
    page = page_on("/storage")
    expect(page.locator("[data-testid='theme']")).to_have_text("light")

    page.locator("[data-testid='theme-dark-btn']").click()
    expect(page.locator("[data-testid='theme']")).to_have_text("dark")
    assert page.evaluate("window.localStorage.getItem('e2e-theme')") == '"dark"'

    page.reload()
    _wait_for_pyscript_init(page, console_messages)
    expect(page.locator("[data-testid='theme']")).to_have_text("dark")


def test_session_storage_write(page_on):
    page = page_on("/storage")
    expect(page.locator("[data-testid='draft']")).to_have_text("")

    page.locator("[data-testid='draft-btn']").click()
    expect(page.locator("[data-testid='draft']")).to_have_text("hello")
    assert page.evaluate("window.sessionStorage.getItem('e2e-draft')") == '"hello"'
