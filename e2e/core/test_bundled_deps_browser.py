import pathlib

import pytest

E2E_DIR = pathlib.Path(__file__).parent

PYSCRIPT_INIT_TIMEOUT = 120_000


@pytest.mark.e2e
class TestBundledDepsBrowser:
    def test_import_aiofiles(self, page, server_url):
        page.goto(f"{server_url}bundled-deps")
        page.wait_for_selector("#webcompy-loading", state="hidden", timeout=PYSCRIPT_INIT_TIMEOUT)
        page.wait_for_selector("#webcompy-app:not([hidden])", timeout=PYSCRIPT_INIT_TIMEOUT)

        page.click('[data-testid="check-aiofiles-btn"]')
        status = page.wait_for_selector('[data-testid="aiofiles-status"]', timeout=30_000)
        text = status.inner_text()
        assert text.startswith("ok:"), f"aiofiles import failed: {text}"
