import pytest
from playwright.sync_api import expect

from e2e.core.conftest import _check_python_errors, _collect_console_messages, _wait_for_pyscript_init

pytestmark = pytest.mark.e2e

SPIKE_PATH = "/storage-sync-spike"


def _open_spike_page(target_page, server_url, console):
    target_page.goto(f"{server_url}{SPIKE_PATH.lstrip('/')}")
    _wait_for_pyscript_init(target_page, console)
    return target_page


@pytest.fixture
def spike_pages(page, context, server_url, console_messages):
    _open_spike_page(page, server_url, console_messages)
    page_b = context.new_page()
    console_b: list = []
    _collect_console_messages(page_b, console_b)
    _open_spike_page(page_b, server_url, console_b)
    yield page, page_b
    page_b.close()
    _check_python_errors(console_b)


def test_remote_write_received_payload_readable_no_self_receive(spike_pages):
    page, page_b = spike_pages
    events = page.locator("[data-testid='storage-event']")

    page_b.evaluate("localStorage.setItem('spike-key', '\"first\"')")
    expect(events.first).to_contain_text("key=spike-key")
    expect(events.first).to_contain_text('newValue="first"')
    expect(events.first).to_contain_text("url=http")

    expect(page_b.locator("[data-testid='storage-event']")).to_have_count(0)

    page_b.locator("[data-testid='write-py-btn']").click()
    expect(events).to_have_count(2)
    expect(events.nth(1)).to_contain_text('newValue="python-write"')
    expect(page_b.locator("[data-testid='storage-event']")).to_have_count(0)


def test_same_value_setitem_and_removal_payload_shapes(spike_pages):
    page, page_b = spike_pages
    events = page.locator("[data-testid='storage-event']")

    page_b.evaluate("localStorage.setItem('spike-key', '\"v\"')")
    expect(events).to_have_count(1)

    page_b.evaluate("localStorage.setItem('spike-key', '\"v\"')")
    page.wait_for_timeout(1500)
    same_value_extra = events.count() - 1
    print(f"spike-observation: same-value setItem produced {same_value_extra} additional event(s)")

    page_b.evaluate("localStorage.removeItem('spike-key')")
    expect(events.last).to_contain_text("newValue=<null>")

    page_b.evaluate("localStorage.setItem('other-key', '\"leftover\"')")
    expect(events).to_have_count(3)

    page_b.evaluate("localStorage.clear()")
    expect(events.last).to_contain_text("key=<null>")
    expect(events.last).to_contain_text("newValue=<null>")


def test_detach_stops_listening(spike_pages):
    page, page_b = spike_pages
    events = page.locator("[data-testid='storage-event']")

    page_b.evaluate("localStorage.setItem('spike-key', '\"before\"')")
    expect(events).to_have_count(1)

    page.locator("[data-testid='detach-btn']").click()
    expect(page.locator("[data-testid='detach-state']")).to_have_text("detached")

    page_b.evaluate("localStorage.setItem('spike-key', '\"after\"')")
    page.wait_for_timeout(1500)
    assert events.count() == 1
