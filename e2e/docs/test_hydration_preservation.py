"""Hydration preservation regression.

Browser hydration SHALL adopt prerendered SSR DOM nodes instead of removing
and rebuilding them. This test instruments the page before PyScript boots,
captures the SSR route roots, and asserts that hydration preserves their
identity, does not leave the page with a mismatch warning, and does not leave
the loading overlay while the routed content is still missing.
"""

import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
def test_route_roots_survive_hydration(page: Page, docs_page_on, docs_console_messages):
    page.add_init_script(
        """
        window.__hydration = { rootsConnected: null, layoutPresent: false, pagePresent: false };
        document.addEventListener('DOMContentLoaded', () => {
          const layout = document.querySelector('docs-layout');
          const pageEl = document.querySelector('quickstart-page');
          window.__hydration.roots = { layout, page: pageEl };
        });
        """
    )

    docs_page_on("/documents/getting-started/quickstart")

    result = page.evaluate(
        """() => {
            const roots = window.__hydration.roots || {};
            return {
                layoutConnected: roots.layout ? roots.layout.isConnected : null,
                pageConnected: roots.page ? roots.page.isConnected : null,
                layoutPresent: !!document.querySelector('docs-layout'),
                pagePresent: !!document.querySelector('quickstart-page'),
            };
        }"""
    )

    assert result["layoutConnected"] is True, (
        f"SSR docs-layout node was destroyed during hydration: {result!r}. "
        "Prerendered route content must be adopted, not rebuilt."
    )
    assert result["pageConnected"] is True, (
        f"SSR page component node was destroyed during hydration: {result!r}. "
        "Prerendered page content must be adopted, not rebuilt."
    )
    assert result["layoutPresent"] and result["pagePresent"]

    hydration_warnings = [
        m.text for m in docs_console_messages if m.type in ("warning", "error") and "Hydration mismatches" in m.text
    ]
    assert not hydration_warnings, f"Hydration mismatches reported on the quickstart page: {hydration_warnings!r}"
    heading_text = page.locator("h1").first.text_content()
    assert heading_text and "Quickstart" in heading_text, f"Page content missing after hydration: {heading_text!r}"


@pytest.mark.e2e
def test_codeblock_token_spans_survive_hydration(page: Page, docs_page_on, docs_console_messages):
    page.add_init_script(
        """
        window.__tok = null;
        document.addEventListener('DOMContentLoaded', () => {
          window.__tok = [...document.querySelectorAll('span[class^="tok-"]')];
        });
        """
    )

    docs_page_on("/documents/getting-started/quickstart")

    result = page.evaluate(
        """() => {
            const tok = window.__tok || [];
            return {
                total: tok.length,
                alive: tok.filter((el) => el.isConnected).length,
            };
        }"""
    )

    assert result["total"] > 0, "No syntax-highlight token spans found on the quickstart page"
    assert result["alive"] == result["total"], (
        f"{result['total'] - result['alive']} of {result['total']} SSR highlight token spans were destroyed "
        f"during hydration: {result!r}. Raw-HTML wrappers must preserve matching child content."
    )

    hydration_warnings = [
        m.text for m in docs_console_messages if m.type in ("warning", "error") and "Hydration mismatches" in m.text
    ]
    assert not hydration_warnings, f"Hydration mismatches reported on the quickstart page: {hydration_warnings!r}"
