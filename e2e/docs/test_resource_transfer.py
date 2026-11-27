import base64
import html
import json
import re
import zlib
from typing import Any

import pytest

_WEBCOMPY_DATA_RE = re.compile(r'<script type="application/json" id="__webcompy_data__">(.*?)</script>', re.DOTALL)


def _fetch_ssr_resources_and_bytes(page, url: str) -> tuple[dict[str, Any], int]:
    resp = page.request.get(url)
    assert resp.ok, f"GET {url} failed with status {resp.status}"
    body = resp.text()
    match = _WEBCOMPY_DATA_RE.search(body)
    assert match is not None, f"__webcompy_data__ script tag missing in {url}"
    data = json.loads(html.unescape(match.group(1)))
    if data.get("__webcompy_compressed__") and isinstance(data.get("data"), str):
        data = json.loads(zlib.decompress(base64.b64decode(data["data"])).decode("utf-8"))
    resources = data.get("resources")
    return (resources if isinstance(resources, dict) else {}), len(body.encode("utf-8"))


@pytest.mark.e2e
def test_documents_page_serves_sidebar_scoped_style(docs_server_url, page):
    page.goto(f"{docs_server_url}documents/getting-started/installation")
    assert page.evaluate(
        "() => Array.from(document.querySelectorAll('style[data-webcompy-cid]'))"
        ".some(s => s.textContent.includes('.docs-sidebar-links'))"
    ), "the sidebar scoped style must be present in the served document, independent of PyScript boot"


@pytest.mark.e2e
def test_static_home_excludes_docs_markdown_bundle(docs_server_url, page, serving_mode):
    if serving_mode != "static":
        pytest.skip("static SSG payload reduction applies to static serving mode")

    resources, html_bytes = _fetch_ssr_resources_and_bytes(page, docs_server_url)
    assert [k for k in resources if k.endswith(".md")] == []
    assert html_bytes < 150_000


@pytest.mark.e2e
def test_static_navigation_fetches_resources_on_demand_and_caches(docs_server_url, docs_page_on, page, serving_mode):
    if serving_mode != "static":
        pytest.skip("SSG transfer guarantee applies to static serving mode")

    baked_resources, _ = _fetch_ssr_resources_and_bytes(
        page, f"{docs_server_url}documents/getting-started/installation/"
    )
    assert "documents/installation.md" in baked_resources
    assert "documents/quickstart.md" not in baked_resources

    resource_requests: list[str] = []
    page.on(
        "request",
        lambda req: resource_requests.append(req.url) if "_webcompy-resource/" in req.url else None,
    )

    page = docs_page_on("/documents/getting-started/installation")
    assert resource_requests == [], f"initial load should use baked payload without refetching: {resource_requests}"

    page.locator(".docs-pager-next a").click()
    page.get_by_role("heading", name="Quickstart").wait_for(state="visible")
    assert any("documents/quickstart.md" in url for url in resource_requests)

    count_after_first = len(resource_requests)
    page.locator(".docs-pager-prev a").click()
    page.get_by_role("heading", name="Installation").wait_for(state="visible")
    page.locator(".docs-pager-next a").click()
    page.get_by_role("heading", name="Quickstart").wait_for(state="visible")
    assert len(resource_requests) == count_after_first, "cached resource should not be fetched twice"


@pytest.mark.e2e
def test_docs_page_head_does_not_duplicate_layout_styles(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/api/server-and-cli")
    style_counts = page.evaluate(
        "() => {"
        "  const styles = [...document.querySelectorAll('style[data-webcompy-cid]')];"
        "  const tocStyles = styles.filter(s => s.textContent.includes('.docs-toc-list'));"
        "  return { total: styles.length, tocCopies: tocStyles.length };"
        "}"
    )
    assert style_counts["tocCopies"] == 0
    assert style_counts["total"] <= 25
