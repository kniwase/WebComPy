import time

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def _seqs(page) -> list[int]:
    items = page.locator("[data-testid='rpc-ws-seq']").all_text_contents()
    return [int(item) for item in items]


def test_rpc_ws_typed_call_round_trip(page_on, serving_mode):
    if serving_mode == "static":
        pytest.skip("WebSocket RPC endpoint exists only in prod mode (asgi-mount)")

    page = page_on("/rpc-ws")
    expect(page.locator("[data-testid='rpc-ws-page']")).to_be_visible()
    expect(page.locator("[data-testid='rpc-ws-state']")).to_have_text("OPEN", timeout=30_000)

    page.locator("[data-testid='rpc-ws-call-btn']").click()
    expect(page.locator("[data-testid='rpc-ws-result']")).to_have_text("ok:5", timeout=30_000)


def test_rpc_ws_subscription_catch_up_after_server_initiated_close(page_on, serving_mode):
    if serving_mode == "static":
        pytest.skip("WebSocket RPC endpoint exists only in prod mode (asgi-mount)")

    page = page_on("/rpc-ws")
    expect(page.locator("[data-testid='rpc-ws-page']")).to_be_visible()
    expect(page.locator("[data-testid='rpc-ws-state']")).to_have_text("OPEN", timeout=30_000)

    # let a few events render (contiguous sequence: 1, 2, 3, ...)
    expect(page.locator("[data-testid='rpc-ws-count']")).not_to_have_text("0", timeout=30_000)
    before = _seqs(page)
    assert before == list(range(1, len(before) + 1)), f"events must start contiguous, got {before}"

    # server-initiated abnormal close via the reserved _webcompy.close notification
    page.locator("[data-testid='rpc-ws-close-btn']").click()
    # the client reconnect loop engages; the server ticker keeps emitting during the outage
    expect(page.locator("[data-testid='rpc-ws-state']")).to_have_text("RECONNECTING", timeout=30_000)
    expect(page.locator("[data-testid='rpc-ws-state']")).to_have_text("OPEN", timeout=30_000)

    # catch-up delivers the missed events exactly once: the sequence stays contiguous
    # (no gaps, no duplicates) while the count keeps growing past the pre-close count
    deadline = time.monotonic() + 30
    after: list[int] = []
    while True:
        after = _seqs(page)
        assert after == list(range(1, len(after) + 1)), (
            f"no gaps or duplicates across the reconnect, got {before} -> {after}"
        )
        if len(after) >= len(before) + 3:
            break
        assert time.monotonic() < deadline, f"event count stuck at {len(after)}"
    assert len(after) > len(before)
