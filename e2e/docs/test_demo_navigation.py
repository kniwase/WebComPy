"""E2E tests for hydration payload lifecycle across docs demo pages.

Covers:
- Initial load of a demo page restores the code block from the SSR transfer
  payload without issuing a main-frame fetch for the demo source.
- SPA navigation between demo pages (helloworld -> fizzbuzz) runs the
  component factory: the code block updates to the new demo's source and the
  main frame fetches the new demo source.
"""

import pytest
from playwright.sync_api import expect

HELLOWORLD_MARKER = "HelloWorld"
FIZZBUZZ_MARKER = "FizzbuzzApp"


@pytest.mark.e2e
def test_initial_load_restores_code_without_main_frame_refetch(docs_page_on, page):
    requests: list[str] = []

    def _on_request(req):
        if req.frame == page.main_frame and "/_demos/helloworld/app.py" in req.url:
            requests.append(req.url)

    page.on("request", _on_request)
    docs_page_on("/sample/helloworld")
    expect(page.locator(".demo-display-root .code-block")).to_contain_text(HELLOWORLD_MARKER)
    page.wait_for_timeout(1500)
    page.remove_listener("request", _on_request)
    assert not requests, f"code was refetched from the main frame: {requests}"


@pytest.mark.e2e
def test_spa_navigation_updates_code_and_fetches_new_source(docs_page_on, page):
    docs_page_on("/sample/helloworld")
    code_block = page.locator(".demo-display-root .code-block")
    expect(code_block).to_contain_text(HELLOWORLD_MARKER)

    requests: list[str] = []

    def _on_request(req):
        if req.frame == page.main_frame and "/_demos/fizzbuzz/app.py" in req.url:
            requests.append(req.url)

    page.on("request", _on_request)
    link = page.locator('a[href="/sample/fizzbuzz/"]').first
    try:
        link.click(timeout=5000)
    except Exception:
        link.evaluate("el => el.click()")

    expect(page.locator(".demo-display-title")).to_have_text("FizzBuzz")
    expect(code_block).to_contain_text(FIZZBUZZ_MARKER)
    page.remove_listener("request", _on_request)
    assert requests, "expected a main-frame fetch of /_demos/fizzbuzz/app.py after navigation"
