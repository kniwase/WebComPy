import pytest


@pytest.mark.e2e
def test_documents_page_serves_sidebar_scoped_style(docs_server_url, page):
    page.goto(f"{docs_server_url}documents/getting-started/installation")
    assert page.evaluate(
        "() => Array.from(document.querySelectorAll('style[data-webcompy-cid]'))"
        ".some(s => s.textContent.includes('.docs-sidebar-links'))"
    ), "the sidebar scoped style must be present in the served document, independent of PyScript boot"


@pytest.mark.e2e
def test_static_navigation_does_not_fetch_resources(docs_page_on, page, serving_mode):
    if serving_mode != "static":
        pytest.skip("the no-fetch guarantee applies to SSG output (static serving mode)")

    resource_requests: list[str] = []
    page.on(
        "request",
        lambda req: resource_requests.append(req.url) if "_webcompy-resource/" in req.url else None,
    )

    page = docs_page_on("/documents/getting-started/installation")
    page.locator(".docs-pager-next a").click()
    page.get_by_role("heading", name="Quickstart").wait_for(state="visible")

    assert resource_requests == [], f"unexpected resource fetches during docs navigation: {resource_requests}"
