import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_mock_fetch_and_rpc(page_on) -> None:
    page = page_on("/rpc-mock")
    expect(page.locator("[data-testid='mock-fetch-result']")).to_contain_text("pending")
    expect(page.locator("[data-testid='mock-rpc-result']")).to_contain_text("pending")

    page.locator("[data-testid='mock-fetch-button']").click()
    expect(page.locator("[data-testid='mock-fetch-result']")).to_contain_text("mock")

    page.locator("[data-testid='mock-rpc-button']").click()
    expect(page.locator("[data-testid='mock-rpc-result']")).to_contain_text("99")
