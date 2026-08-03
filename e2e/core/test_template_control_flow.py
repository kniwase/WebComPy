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


class TestTemplateControlFlowBrowser:
    def test_page_renders(self, page_on):
        page = page_on("/template-control-flow")
        expect(page.locator("[data-testid='template-control-flow-page']")).to_be_visible()
        expect(page.locator("h2")).to_have_text("Template Control Flow Tests")

    def test_static_if_renders_visible_branch_by_default(self, page_on):
        page = page_on("/template-control-flow")
        expect(page.locator("[data-testid='if-visible']")).to_be_visible()
        expect(page.locator("[data-testid='if-hidden']")).to_have_count(0)

    def test_static_for_renders_visible_iterations(self, page_on):
        page = page_on("/template-control-flow")
        items = page.locator("[data-testid='for-li']")
        expect(items).to_have_count(2)
        expect(items.nth(0)).to_have_text("alpha")
        expect(items.nth(1)).to_have_text("gamma")

    def test_signal_change_switches_branch(self, page_on):
        page = page_on("/template-control-flow")
        expect(page.locator("[data-testid='if-visible']")).to_be_visible()
        page.locator("[data-testid='toggle-btn']").click()
        expect(page.locator("[data-testid='if-hidden']")).to_be_visible()
        expect(page.locator("[data-testid='if-visible']")).to_have_count(0)
        page.locator("[data-testid='toggle-btn']").click()
        expect(page.locator("[data-testid='if-visible']")).to_be_visible()
        expect(page.locator("[data-testid='if-hidden']")).to_have_count(0)

    def test_signal_count_updates(self, page_on):
        page = page_on("/template-control-flow")
        expect(page.locator("[data-testid='count']")).to_have_text("0")
        page.locator("[data-testid='increment-btn']").click()
        expect(page.locator("[data-testid='count']")).to_have_text("1")

    def test_loop_metadata_static_items(self, page_on):
        page = page_on("/template-control-flow")
        items = page.locator("[data-testid='loop-meta-static-item']")
        expect(items).to_have_count(3)
        expect(items.nth(0)).to_have_text("1,True,False,3:alpha")
        expect(items.nth(1)).to_have_text("2,False,False,3:beta")
        expect(items.nth(2)).to_have_text("3,False,True,3:gamma")

    def test_loop_metadata_dict_initial(self, page_on):
        page = page_on("/template-control-flow")
        items = page.locator("[data-testid='loop-meta-dict-item']")
        expect(items).to_have_count(3)
        expect(items.nth(0)).to_have_text("1,True,False,3:1")
        expect(items.nth(1)).to_have_text("2,False,False,3:2")
        expect(items.nth(2)).to_have_text("3,False,True,3:3")

    def test_loop_metadata_dict_updates_on_reorder(self, page_on):
        page = page_on("/template-control-flow")
        items = page.locator("[data-testid='loop-meta-dict-item']")
        page.locator("[data-testid='loop-dict-mutate']").click()
        expect(items).to_have_count(3)
        expect(items.nth(0)).to_have_text("1,True,False,3:2")
        expect(items.nth(1)).to_have_text("2,False,False,3:3")
        expect(items.nth(2)).to_have_text("3,False,True,3:1")
        page.locator("[data-testid='loop-dict-mutate']").click()
        expect(items.nth(0)).to_have_text("1,True,False,3:3")
        expect(items.nth(1)).to_have_text("2,False,False,3:1")
        expect(items.nth(2)).to_have_text("3,False,True,3:2")


class TestTemplateControlFlowSSR:
    def test_static_html_includes_branch_and_iterations(self, static_site):
        dist_dir, _wheel_file, _app_name = static_site
        html_content = (dist_dir / "template-control-flow" / "index.html").read_text(encoding="utf-8")
        assert 'data-testid="template-control-flow-page"' in html_content
        assert 'data-testid="if-visible"' in html_content
        assert 'data-testid="if-hidden"' not in html_content
        assert "alpha" in html_content
        assert "gamma" in html_content
        assert "beta" not in html_content.split('data-testid="for-list"')[1].split("</ul>")[0]

    def test_static_html_includes_loop_metadata(self, static_site):
        dist_dir, _wheel_file, _app_name = static_site
        html_content = (dist_dir / "template-control-flow" / "index.html").read_text(encoding="utf-8")
        assert "1,True,False,3:alpha" in html_content
        assert "3,False,True,3:gamma" in html_content
        assert "1,True,False,3:1" in html_content
        assert "3,False,True,3:3" in html_content

    def test_hydration_payload_includes_signals(self, static_site):
        dist_dir, _wheel_file, _app_name = static_site
        html_content = (dist_dir / "template-control-flow" / "index.html").read_text(encoding="utf-8")
        payload = _read_payload(html_content)
        assert payload is not None
        assert "signals" in payload
        assert isinstance(payload["signals"], dict)
