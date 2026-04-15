from playwright.sync_api import expect


def test_function_style_component(page_on):
    page = page_on("/component")
    expect(page.locator("[data-testid='function-style-page']")).to_be_visible()
    expect(page.locator("[data-testid='function-msg']")).to_have_text("Hello from function component!")


def test_class_style_component(page_on):
    page = page_on("/component/classstyle")
    expect(page.locator("[data-testid='class-style-page']")).to_be_visible()
    expect(page.locator("[data-testid='class-msg']")).to_have_text("Hello from class component!")
