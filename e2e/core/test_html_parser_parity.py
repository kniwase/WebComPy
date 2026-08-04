from __future__ import annotations

import json

import pytest
from my_app.parity_fixtures import compute_parity_results
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_html_parser_environment_parity(page_on):
    page = page_on("/html-parser-parity")
    locator = page.locator("[data-testid='parity-result']")
    expect(locator).not_to_have_text("", timeout=30_000)
    browser_results = json.loads(locator.inner_text())
    assert browser_results["tree"] == compute_parity_results()


def test_adjacent_text_nodes_merge_in_parsed_dom(page_on):
    page = page_on("/html-parser-parity")
    locator = page.locator("[data-testid='parity-result']")
    expect(locator).not_to_have_text("", timeout=30_000)
    browser_results = json.loads(locator.inner_text())
    assert browser_results["tree"]["adjacent_text"] == ["tree", "div[](#text('a');#text('x');#text('b'))"]
    assert browser_results["dom"]["adjacent_text"] == "div(#text('a{{ x }}b'))"
