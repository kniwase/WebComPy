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


def test_template_page_renders_structure(page_on):
    page = page_on("/template")
    expect(page.locator("[data-testid='template-page']")).to_be_visible()
    expect(page.locator("h2")).to_have_text("Template Engine Tests")
    expect(page.locator("[data-testid='static-text']")).to_have_text("static content")
    expect(page.locator("[data-testid='item-1']")).to_have_text("Item 1")
    expect(page.locator("[data-testid='item-2']")).to_have_text("Item 2")


def test_template_signal_text_updates(page_on):
    page = page_on("/template")
    expect(page.locator("[data-testid='count']")).to_have_text("0")
    page.locator("[data-testid='increment-btn']").click()
    expect(page.locator("[data-testid='count']")).to_have_text("1")
    page.locator("[data-testid='increment-btn']").click()
    expect(page.locator("[data-testid='count']")).to_have_text("2")


def test_template_void_elements_render(page_on):
    page = page_on("/template")
    expect(page.locator("[data-testid='disabled-input']")).to_be_visible()
    is_disabled = page.locator("[data-testid='disabled-input']").evaluate("el => el.hasAttribute('disabled')")
    assert is_disabled is True


def test_template_ssr_html_structure(static_site):
    dist_dir, _wheel_file, _app_name = static_site
    html_content = (dist_dir / "template" / "index.html").read_text(encoding="utf-8")
    assert 'data-testid="template-page"' in html_content
    assert "Template Engine Tests" in html_content
    assert "Item 1" in html_content
    assert "Item 2" in html_content
    assert "disabled" in html_content


def test_template_ssr_hydration_payload_signals_section(static_site):
    dist_dir, _wheel_file, _app_name = static_site
    html_content = (dist_dir / "template" / "index.html").read_text(encoding="utf-8")
    payload = _read_payload(html_content)
    assert payload is not None, "Hydration payload script not found in static HTML"
    assert "signals" in payload
    assert isinstance(payload["signals"], dict)
