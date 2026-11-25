import time

import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import PYSCRIPT_INIT_TIMEOUT, PYSCRIPT_POLL_INTERVAL

pytestmark = pytest.mark.e2e


def _wait_for_peer_iframe(page, title: str):
    start_time = time.monotonic()
    selector = f'iframe[title="{title}"]'
    while True:
        try:
            page.wait_for_selector(selector, timeout=PYSCRIPT_POLL_INTERVAL)
            element = page.query_selector(selector)
            if element is None:
                raise Exception(f"iframe {title!r} not found")
            frame = element.content_frame()
            if frame is None:
                raise Exception(f"iframe {title!r} has no content frame")
            frame.locator("#webcompy-loading").wait_for(state="hidden", timeout=PYSCRIPT_POLL_INTERVAL)
            frame.locator("#webcompy-app:not([hidden])").wait_for(timeout=PYSCRIPT_POLL_INTERVAL)
            return frame
        except Exception:
            pass
        if time.monotonic() - start_time > PYSCRIPT_INIT_TIMEOUT / 1000:
            pytest.fail(f"Peer iframe {title!r} PyScript did not initialize cleanly")


def test_examples_storage_sync_between_peer_windows(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/storage-sync")
    page.set_viewport_size({"width": 1280, "height": 900})
    assert page.title() == "Storage Sync - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text("Storage Sync")
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()

    new_tab_link = page.get_by_role("link", name="Open demo in new tab")
    expect(new_tab_link).to_be_visible()
    assert new_tab_link.get_attribute("href") == "/documents/examples/storage-sync/"

    frame_a = _wait_for_peer_iframe(page, "Window A")
    frame_b = _wait_for_peer_iframe(page, "Window B")

    frame_a.get_by_role("button", name="Reset").click()
    expect(frame_a.locator(".status-theme")).to_have_text("Theme: ocean")
    expect(frame_b.locator(".status-theme")).to_have_text("Theme: ocean")

    frame_a.get_by_role("button", name="Forest").click()
    frame_a.get_by_role("button", name="+1 Counter").click()
    expect(frame_b.locator(".status-theme")).to_have_text("Theme: forest")
    expect(frame_b.locator(".status-count")).to_have_text("Count: 1")
