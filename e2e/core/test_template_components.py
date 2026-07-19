from __future__ import annotations

import html as html_module
import json
import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

_HYDRATION_DATA_RE = re.compile(
    r'<script type="application/json" id="__webcompy_data__">(.*?)</script>',
    re.DOTALL,
)


def _read_payload(html_content: str) -> dict | None:
    match = _HYDRATION_DATA_RE.search(html_content)
    if match is None:
        return None
    return json.loads(html_module.unescape(match.group(1)))


def test_template_components_page_renders(page_on):
    """Pre-rendered HTML from the component-tag page is correctly structured."""
    page = page_on("/template-components")
    expect(page.locator("[data-testid='template-components-page']")).to_be_visible()
    expect(page.locator("h2")).to_have_text("Component Tags")
    expect(page.locator("[data-testid='card-count']")).to_be_visible()
    expect(page.locator("[data-testid='card-greeting']")).to_have_text("Hello, Component Tag!")
    expect(page.locator("[data-testid='card-count-value']")).to_have_text("5")
    expect(page.locator("[data-testid='nested-count']")).to_be_visible()
    expect(page.locator("[data-testid='nested-count-value']")).to_have_text("5")


def test_template_components_reactive_signal_updates(page_on):
    """`:count="signal"` propagates into the child component after hydration."""
    page = page_on("/template-components")
    expect(page.locator("[data-testid='card-count-value']")).to_have_text("5")
    page.locator("[data-testid='card-increment']").click()
    expect(page.locator("[data-testid='card-count-value']")).to_have_text("6")
    expect(page.locator("[data-testid='nested-count-value']")).to_have_text("6")
    page.locator("[data-testid='card-increment']").click()
    expect(page.locator("[data-testid='card-count-value']")).to_have_text("7")
    expect(page.locator("[data-testid='nested-count-value']")).to_have_text("7")


def test_template_components_ssr_includes_child_output(static_site):
    """Static site build embeds the component-tag children in the prerendered HTML."""
    dist_dir, _wheel_file, _app_name = static_site
    html_content = (dist_dir / "template-components" / "index.html").read_text(encoding="utf-8")
    assert 'data-testid="template-components-page"' in html_content
    assert 'data-testid="card-count"' in html_content
    assert "Hello, Component Tag!" in html_content
    assert 'data-testid="card-count-value"' in html_content
    # Nested component tag should render too
    assert 'data-testid="nested-count"' in html_content
    assert 'data-testid="nested-count-value"' in html_content


def test_template_components_ssr_payload_signals_section(static_site):
    dist_dir, _wheel_file, _app_name = static_site
    html_content = (dist_dir / "template-components" / "index.html").read_text(encoding="utf-8")
    payload = _read_payload(html_content)
    assert payload is not None, "Hydration payload script not found in static HTML"
    assert "signals" in payload
    assert isinstance(payload["signals"], dict)
