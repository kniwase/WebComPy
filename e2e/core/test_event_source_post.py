import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_sse_post_events_and_reconnect(page_on, serving_mode):
    if serving_mode == "static":
        pytest.skip("SSE endpoint exists only in prod mode (asgi-mount)")

    page = page_on("/event-source-post")
    expect(page.locator("[data-testid='sse-post-page']")).to_be_visible()

    # First response carries the echoed body plus ping-1..3; the reconnect
    # (which requires Last-Event-ID) carries ping-4..6.
    expect(page.locator("[data-testid='sse-post-item']")).to_have_text(
        ['echo:{"q":"x"}', "ping-1", "ping-2", "ping-3", "ping-4", "ping-5", "ping-6"],
        timeout=30_000,
    )
    expect(page.locator("[data-testid='sse-post-state']")).to_have_text("OPEN", timeout=30_000)
