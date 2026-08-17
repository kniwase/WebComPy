import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_websocket_round_trip_and_connection_is_shared(page_on, serving_mode):
    if serving_mode == "static":
        pytest.skip("WebSocket endpoint exists only in prod mode (asgi-mount)")

    page = page_on("/websocket")
    expect(page.locator("[data-testid='ws-page']")).to_be_visible()

    expect(page.locator("[data-testid='state-a']")).to_have_text("OPEN", timeout=30_000)
    expect(page.locator("[data-testid='state-b']")).to_have_text("OPEN", timeout=30_000)

    conn_a = page.locator("[data-testid='conn-a']").text_content()
    conn_b = page.locator("[data-testid='conn-b']").text_content()
    assert conn_a
    assert conn_a == conn_b

    page.locator("[data-testid='send-btn']").click()
    expect(page.locator("[data-testid='message-a-item']")).to_have_text(["echo:hello"], timeout=30_000)
    expect(page.locator("[data-testid='message-b-item']")).to_have_text(["echo:hello"], timeout=30_000)


def test_websocket_reconnects_after_server_initiated_close(page_on, serving_mode):
    if serving_mode == "static":
        pytest.skip("WebSocket endpoint exists only in prod mode (asgi-mount)")

    page = page_on("/websocket")
    expect(page.locator("[data-testid='ws-page']")).to_be_visible()

    expect(page.locator("[data-testid='state-a']")).to_have_text("OPEN", timeout=30_000)
    conn_a_before = page.locator("[data-testid='conn-a']").text_content()
    assert conn_a_before

    page.locator("[data-testid='kill-btn']").click()

    expect(page.locator("[data-testid='conn-a']")).not_to_have_text(conn_a_before, timeout=30_000)
    expect(page.locator("[data-testid='state-a']")).to_have_text("OPEN", timeout=30_000)
    expect(page.locator("[data-testid='last-close-a']")).to_have_text("1011", timeout=30_000)


def test_typed_websocket_round_trip_and_malformed_frame_is_skipped(page_on, serving_mode):
    if serving_mode == "static":
        pytest.skip("WebSocket endpoint exists only in prod mode (asgi-mount)")

    page = page_on("/websocket")
    expect(page.locator("[data-testid='ws-page']")).to_be_visible()

    expect(page.locator("[data-testid='typed-state']")).to_have_text("OPEN", timeout=30_000)

    page.locator("[data-testid='typed-roundtrip-btn']").click()
    expect(page.locator("[data-testid='typed-message-item']")).to_have_text(
        ["ada:hello:2025-01-02T03:04:05"], timeout=30_000
    )
    expect(page.locator("[data-testid='typed-error']")).to_have_text("", timeout=30_000)

    page.locator("[data-testid='typed-bad-btn']").click()
    expect(page.locator("[data-testid='typed-error']")).not_to_have_text("", timeout=30_000)

    page.locator("[data-testid='typed-roundtrip-btn']").click()
    expect(page.locator("[data-testid='typed-message-item']")).to_have_text(
        ["ada:hello:2025-01-02T03:04:05", "ada:hello:2025-01-02T03:04:05"], timeout=30_000
    )
    expect(page.locator("[data-testid='typed-error']")).to_have_text("", timeout=30_000)
