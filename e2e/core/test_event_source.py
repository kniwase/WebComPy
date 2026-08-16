import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_sse_events_render_and_connection_is_shared(page_on, serving_mode):
    if serving_mode == "static":
        pytest.skip("SSE endpoint exists only in prod mode (asgi-mount)")

    page = page_on("/event-source")
    expect(page.locator("[data-testid='sse-page']")).to_be_visible()

    expect(page.locator("[data-testid='state-a']")).to_have_text("OPEN", timeout=30_000)
    expect(page.locator("[data-testid='state-b']")).to_have_text("OPEN", timeout=30_000)

    expect(page.locator("[data-testid='message-a-item']")).to_have_text(["ping-1", "ping-2", "ping-3"], timeout=30_000)
    expect(page.locator("[data-testid='message-b-item']")).to_have_text(["ping-1", "ping-2", "ping-3"], timeout=30_000)

    session_a = page.locator("[data-testid='session-a']").text_content()
    session_b = page.locator("[data-testid='session-b']").text_content()
    assert session_a
    assert session_a == session_b
