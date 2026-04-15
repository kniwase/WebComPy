from playwright.sync_api import expect


def test_lifecycle_hooks_fire(page_on):
    page = page_on("/lifecycle")
    expect(page.locator("[data-testid='lifecycle-page']")).to_be_visible()
    expect(page.locator("[data-testid='render-count']")).to_have_text("1")


def test_on_after_rendering_on_interactions(page_on):
    page = page_on("/lifecycle")
    page.locator("[data-testid='lifecycle-increment-btn']").click()
    expect(page.locator("[data-testid='lifecycle-count']")).to_have_text("1")
    expect(page.locator("[data-testid='render-count']")).to_have_text("1")


def test_on_before_rendering_on_navigation(app_page):
    app_page.locator("[data-testid='nav-lifecycle']").click()
    expect(app_page.locator("[data-testid='lifecycle-page']")).to_be_visible()

    app_page.locator("[data-testid='lifecycle-increment-btn']").click()
    expect(app_page.locator("[data-testid='lifecycle-count']")).to_have_text("1")

    app_page.locator("[data-testid='nav-home']").click()
    app_page.locator("[data-testid='nav-lifecycle']").click()
    expect(app_page.locator("[data-testid='lifecycle-page']")).to_be_visible()
    expect(app_page.locator("[data-testid='lifecycle-count']")).to_have_text("0")
