import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def _items(page) -> list[str]:
    return page.locator("[data-testid='rpc-stream-item']").all_text_contents()


def _skip_static(serving_mode) -> None:
    if serving_mode == "static":
        pytest.skip("RPC streaming endpoint exists only in prod mode (asgi-mount)")


def test_http_stream_typed_items_then_done(page_on, serving_mode):
    _skip_static(serving_mode)
    page = page_on("/rpc-stream")
    expect(page.locator("[data-testid='rpc-stream-page']")).to_be_visible()

    page.locator("[data-testid='rpc-stream-http-btn']").click()
    expect(page.locator("[data-testid='rpc-stream-status']")).to_have_text("closed", timeout=30_000)
    assert _items(page) == ["1", "2", "3", "4", "5"]


def test_http_sync_stream_items_then_done(page_on, serving_mode):
    _skip_static(serving_mode)
    page = page_on("/rpc-stream")
    expect(page.locator("[data-testid='rpc-stream-page']")).to_be_visible()

    page.locator("[data-testid='rpc-stream-http-sync-btn']").click()
    expect(page.locator("[data-testid='rpc-stream-status']")).to_have_text("closed", timeout=30_000)
    assert _items(page) == ["1", "2", "3"]


def test_http_stream_mid_stream_error(page_on, serving_mode):
    _skip_static(serving_mode)
    page = page_on("/rpc-stream")
    expect(page.locator("[data-testid='rpc-stream-page']")).to_be_visible()

    page.locator("[data-testid='rpc-stream-http-error-btn']").click()
    expect(page.locator("[data-testid='rpc-stream-status']")).to_have_text("failed", timeout=30_000)
    expect(page.locator("[data-testid='rpc-stream-message']")).to_contain_text("RPC error")
    assert _items(page) == ["1", "2"]


def test_ws_stream_items_then_done(page_on, serving_mode):
    _skip_static(serving_mode)
    page = page_on("/rpc-stream")
    expect(page.locator("[data-testid='rpc-stream-page']")).to_be_visible()
    expect(page.locator("[data-testid='rpc-stream-status']")).to_have_text("idle", timeout=30_000)

    page.locator("[data-testid='rpc-stream-ws-btn']").click()
    expect(page.locator("[data-testid='rpc-stream-status']")).to_have_text("closed", timeout=30_000)
    assert _items(page) == ["1", "2", "3", "4", "5"]


def test_ws_sync_stream_items_then_done(page_on, serving_mode):
    _skip_static(serving_mode)
    page = page_on("/rpc-stream")
    expect(page.locator("[data-testid='rpc-stream-page']")).to_be_visible()
    expect(page.locator("[data-testid='rpc-stream-status']")).to_have_text("idle", timeout=30_000)

    page.locator("[data-testid='rpc-stream-ws-sync-btn']").click()
    expect(page.locator("[data-testid='rpc-stream-status']")).to_have_text("closed", timeout=30_000)
    assert _items(page) == ["1", "2", "3", "4", "5"]


def test_ws_stream_mid_stream_error(page_on, serving_mode):
    _skip_static(serving_mode)
    page = page_on("/rpc-stream")
    expect(page.locator("[data-testid='rpc-stream-page']")).to_be_visible()

    page.locator("[data-testid='rpc-stream-ws-error-btn']").click()
    expect(page.locator("[data-testid='rpc-stream-status']")).to_have_text("failed", timeout=30_000)
    assert _items(page) == ["1", "2"]
