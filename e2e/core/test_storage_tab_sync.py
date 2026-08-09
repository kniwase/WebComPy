import pytest
from playwright.sync_api import expect

from e2e.core.conftest import _check_python_errors, _collect_console_messages, _wait_for_pyscript_init

pytestmark = pytest.mark.e2e

SYNC_PATH = "/storage-tab-sync"


def _open_sync_page(target_page, server_url, console):
    target_page.goto(f"{server_url}{SYNC_PATH.lstrip('/')}")
    _wait_for_pyscript_init(target_page, console)
    return target_page


@pytest.fixture
def sync_pages(page, context, server_url, console_messages):
    _open_sync_page(page, server_url, console_messages)
    page_b = context.new_page()
    console_b: list = []
    _collect_console_messages(page_b, console_b)
    _open_sync_page(page_b, server_url, console_b)
    yield page, page_b
    page_b.close()
    _check_python_errors(console_b)


def test_signal_write_in_other_tab_updates_ui(sync_pages):
    page, page_b = sync_pages
    expect(page.locator("[data-testid='synced-value']")).to_have_text("initial")

    page_b.locator("[data-testid='write-btn']").click()
    expect(page.locator("[data-testid='synced-value']")).to_have_text("from-button")
    expect(page_b.locator("[data-testid='synced-value']")).to_have_text("from-button")


def test_raw_set_item_in_other_tab_updates_ui(sync_pages):
    page, page_b = sync_pages
    expect(page.locator("[data-testid='synced-value']")).to_have_text("initial")

    page_b.evaluate("localStorage.setItem('e2e-synced', '\"from-b\"')")
    expect(page.locator("[data-testid='synced-value']")).to_have_text("from-b")


def test_raw_remove_item_in_other_tab_resets_ui(sync_pages):
    page, page_b = sync_pages
    expect(page.locator("[data-testid='synced-value']")).to_have_text("initial")

    page_b.evaluate("localStorage.setItem('e2e-synced', '\"from-b\"')")
    expect(page.locator("[data-testid='synced-value']")).to_have_text("from-b")

    page_b.evaluate("localStorage.removeItem('e2e-synced')")
    expect(page.locator("[data-testid='synced-value']")).to_have_text("initial")
