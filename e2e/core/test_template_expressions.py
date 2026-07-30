from __future__ import annotations

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


class TestTemplateExpressionsBrowser:
    def test_page_renders(self, page_on):
        page = page_on("/template-expressions")
        expect(page.locator("[data-testid='template-expressions-page']")).to_be_visible()
        expect(page.locator("h2")).to_have_text("Template Expressions Tests")

    def test_arithmetic_expression(self, page_on):
        page = page_on("/template-expressions")
        expect(page.locator("[data-testid='arith']")).to_have_text("6")

    def test_filter_expression(self, page_on):
        page = page_on("/template-expressions")
        expect(page.locator("[data-testid='filtered']")).to_have_text("ALICE")

    def test_subscript_expression(self, page_on):
        page = page_on("/template-expressions")
        expect(page.locator("[data-testid='sub']")).to_have_text("4")

    def test_reactive_if_expression(self, page_on):
        page = page_on("/template-expressions")
        expect(page.locator("[data-testid='reactive-if']")).to_have_text("<=5")
        page.locator("[data-testid='increment-btn']").click()
        expect(page.locator("[data-testid='reactive-if']")).to_have_text(">5")

    def test_for_slice_expression(self, page_on):
        page = page_on("/template-expressions")
        items = page.locator("[data-testid='for-li']")
        expect(items).to_have_count(3)
        expect(items.nth(0)).to_have_text("1")
        expect(items.nth(1)).to_have_text("2")
        expect(items.nth(2)).to_have_text("3")

    def test_for_slice_updates_on_list_mutation(self, page_on):
        page = page_on("/template-expressions")
        page.locator("[data-testid='remove-first-btn']").click()
        items = page.locator("[data-testid='for-li']")
        expect(items).to_have_count(3)
        expect(items.nth(0)).to_have_text("2")
        expect(items.nth(1)).to_have_text("3")
        expect(items.nth(2)).to_have_text("4")

    def test_raw_block_output(self, page_on):
        page = page_on("/template-expressions")
        expect(page.locator("[data-testid='raw-output']")).to_have_text("{{ literal }}")

    def test_comment_stripped(self, page_on):
        page = page_on("/template-expressions")
        expect(page.locator("[data-testid='comment-output']")).to_have_text("Hello!")
