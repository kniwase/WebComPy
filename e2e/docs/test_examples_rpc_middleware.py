import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe

pytestmark = pytest.mark.e2e


def test_examples_rpc_middleware_synthesizes_without_network(page, docs_page_on, assert_no_console_errors):
    rpc_requests: list[str] = []
    page.on("request", lambda req: rpc_requests.append(req.url) if "/_webcompy-rpc" in req.url else None)

    docs_page_on("/documents/examples/rpc-middleware")
    assert page.title() == "RPC Middleware - WebComPy Docs"
    expect(page.locator("article.prose h1")).to_have_text("RPC Middleware")
    expect(page.get_by_role("heading", name="Real server wiring")).to_be_visible()
    expect(page.get_by_role("heading", name="Next steps")).to_be_visible()

    frame = _wait_for_demo_iframe(page, "rpc_middleware_mock")
    frame.get_by_role("button", name="Monitor").click()
    frame.get_by_role("button", name="+").click()
    frame.get_by_role("button", name="Request Quote").click()
    expect(frame.locator(".quote-result")).to_have_text("3x Monitor @ $340 -> Total: $1020")

    frame.get_by_role("button", name="Run Batch").click()
    expect(frame.locator(".batch-result")).to_have_text("Catalog size: 3 items (USD)")
    expect(frame.locator(".log-list")).to_contain_text("batch([orders.quote, catalog.summary])")
    assert rpc_requests == []
