import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_async_guard_redirects_to_login(app_page):
    app_page.locator("[data-testid='nav-admin']").click()
    expect(app_page).to_have_url(re.compile(r"/login"))
    expect(app_page.locator("[data-testid='login-page']")).to_be_visible()
    expect(app_page.locator("[data-testid='admin-page']")).to_have_count(0)


def test_back_after_redirect_does_not_loop(app_page):
    app_page.locator("[data-testid='nav-reactive']").click()
    expect(app_page).to_have_url(re.compile(r"/reactive"))
    app_page.locator("[data-testid='nav-admin']").click()
    expect(app_page).to_have_url(re.compile(r"/login"))
    app_page.go_back()
    expect(app_page).to_have_url(re.compile(r"/$"))
    expect(app_page.locator("[data-testid='home-page']")).to_be_visible()


def test_login_then_admin_allowed(app_page):
    app_page.locator("[data-testid='nav-admin']").click()
    expect(app_page.locator("[data-testid='login-page']")).to_be_visible()
    app_page.locator("[data-testid='login-button']").click()
    expect(app_page).to_have_url(re.compile(r"/admin"))
    expect(app_page.locator("[data-testid='admin-page']")).to_be_visible()
