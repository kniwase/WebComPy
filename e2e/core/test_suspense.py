from __future__ import annotations

import json
import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


class TestSuspenseElement:
    def test_suspense_page_loads(self, app_page, assert_no_console_errors):
        app_page.locator("[data-testid='nav-suspense']").click()
        expect(app_page.locator("[data-testid='suspense-page']")).to_be_visible()

    def test_suspense_direct_url(self, page_on):
        page = page_on("/suspense")
        expect(page.locator("[data-testid='suspense-page']")).to_be_visible()

    def test_suspense_resolves(self, page_on, assert_no_console_errors):
        page = page_on("/suspense")
        expect(page.locator("[data-testid='suspense-data']")).to_be_attached(timeout=30000)


class TestHydrationDataTransfer:
    def test_ssg_output_contains_webcompy_data(self, static_site):
        dist_dir, _wheel_file, _app_name = static_site
        html_content = (dist_dir / "index.html").read_text(encoding="utf-8")
        assert "__webcompy_data__" in html_content

    def test_payload_is_valid_json(self, static_site):
        dist_dir, _wheel_file, _app_name = static_site
        html_content = (dist_dir / "index.html").read_text(encoding="utf-8")
        match = re.search(
            r'<script type="application/json" id="__webcompy_data__">(.*?)</script>',
            html_content,
        )
        assert match is not None
        import html as html_module

        decoded = html_module.unescape(match.group(1))
        payload = json.loads(decoded)
        assert payload["__webcompy_transfer_version__"] == 2
        assert "fetches" in payload
        assert "async_results" in payload
        assert "signals" in payload

    def test_payload_removed_after_hydration(self, page_on):
        page = page_on("/")
        el_count = page.locator("#__webcompy_data__").count()
        assert el_count == 0

    def test_normal_async_fallthrough(self, page_on):
        page = page_on("/async-nav")
        expect(page.locator("[data-testid='async-nav-page']")).to_be_visible()
