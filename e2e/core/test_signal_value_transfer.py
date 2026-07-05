from __future__ import annotations

import html as html_module
import json
import re

import pytest

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


class TestSignalHydrationPayloadStructure:
    """Verify the SSG payload exposes the signals section.

    The signal-value-transfer feature targets `self`-assigned Signals on
    Component instances (which populate ``__signal_members__``). The
    WebComPy my-app demo uses function-style ``@define_component`` and
    therefore stores Signals as local variables — those do not flow
    through ``__signal_members__`` and the payload's ``signals`` section
    is empty for those components. These tests assert the payload
    shape so future changes to the schema are caught even when the
    demo app contains no transferable Signals.
    """

    def test_payload_includes_signals_section(self, static_site):
        dist_dir, _wheel_file, _app_name = static_site
        html_content = (dist_dir / "index.html").read_text(encoding="utf-8")
        payload = _read_payload(html_content)
        assert payload is not None
        assert "signals" in payload
        assert isinstance(payload["signals"], dict)

    def test_payload_version_is_two(self, static_site):
        dist_dir, _wheel_file, _app_name = static_site
        html_content = (dist_dir / "index.html").read_text(encoding="utf-8")
        payload = _read_payload(html_content)
        assert payload is not None
        assert payload["__webcompy_transfer_version__"] == 2


class TestSignalHydrationNoRegression:
    """Verify the existing Signal-based pages still hydrate cleanly.

    The /reactive page uses local-variable Signals. Adding the signals
    transfer pipeline must not break its hydration: the transferred
    empty/passthrough signals section should not interfere with the
    local signals, the loading indicator should disappear, and the
    page should be interactive without console errors.
    """

    def test_reactive_page_hydrates_with_intact_local_signals(self, page_on, assert_no_console_errors):
        page = page_on("/reactive")
        page.wait_for_selector("#webcompy-loading", state="hidden", timeout=30000)
        page.wait_for_selector("#webcompy-app:not([hidden])", timeout=30000)
        page.wait_for_selector("[data-testid='reactive-page']", timeout=30000)

        from playwright.sync_api import expect

        expect(page.locator("[data-testid='count']")).to_have_text("0")
        expect(page.locator("[data-testid='doubled']")).to_have_text("0")

        page.locator("[data-testid='increment-btn']").click()
        expect(page.locator("[data-testid='count']")).to_have_text("1")
        expect(page.locator("[data-testid='doubled']")).to_have_text("2")

        page.locator("[data-testid='list-add-btn']").click()
        expect(page.locator("[data-testid='list-count']")).to_have_text("4")
