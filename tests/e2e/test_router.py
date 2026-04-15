import re

from playwright.sync_api import expect


def test_router_link_navigation(app_page):
    expect(app_page.locator("[data-testid='home-page']")).to_be_visible()

    app_page.locator("[data-testid='nav-reactive']").click()
    expect(app_page).to_have_url(re.compile(r"/reactive"))
    expect(app_page.locator("[data-testid='reactive-page']")).to_be_visible()


def test_router_link_to_home(app_page):
    app_page.locator("[data-testid='nav-reactive']").click()
    expect(app_page.locator("[data-testid='reactive-page']")).to_be_visible()

    app_page.locator("[data-testid='nav-home']").click()
    expect(app_page).to_have_url(re.compile(r"/WebComPy"))
    expect(app_page.locator("[data-testid='home-page']")).to_be_visible()


def test_not_found_route(page_on):
    page = page_on("/nonexistent-route")
    expect(page.locator("[data-testid='not-found']")).to_be_visible()
    expect(page.locator("[data-testid='not-found-path']")).to_contain_text("nonexistent-route")


def test_page_title_on_navigation(app_page):
    expect(app_page).to_have_title("Home - E2E")

    app_page.locator("[data-testid='nav-reactive']").click()
    expect(app_page).to_have_title("Reactive - E2E")


def test_browser_back_forward(app_page):
    expect(app_page.locator("[data-testid='home-page']")).to_be_visible()

    app_page.locator("[data-testid='nav-reactive']").click()
    expect(app_page.locator("[data-testid='reactive-page']")).to_be_visible()

    app_page.go_back()
    expect(app_page.locator("[data-testid='home-page']")).to_be_visible()

    app_page.go_forward()
    expect(app_page.locator("[data-testid='reactive-page']")).to_be_visible()
