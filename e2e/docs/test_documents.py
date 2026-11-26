import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_pyscript_init


@pytest.mark.e2e
def test_documents_index_shows_section_cards(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents")
    expect(page.get_by_role("heading", name="Documentation")).to_be_visible()
    expect(page.get_by_role("heading", name="Getting Started")).to_be_visible()
    expect(page.get_by_text("Operators' cheat sheet")).to_be_visible()
    expect(page.get_by_role("link", name="Open Installation")).to_be_visible()
    expect(page.get_by_role("link", name="Open Signals and Streams")).to_be_visible()
    expect(page.get_by_role("link", name="Open CLI Reference")).to_be_visible()
    expect(page.get_by_role("link", name="Open Hello World")).to_be_visible()
    expect(page.get_by_role("link", name="Open From Jinja2 + FastAPI")).to_be_visible()
    expect(page.get_by_role("link", name="Open App & Components")).to_be_visible()


@pytest.mark.e2e
def test_documents_page_content(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents")
    expect(page.get_by_role("heading", name="Getting Started")).to_be_visible()
    expect(page.get_by_role("heading", name="Guides")).to_be_visible()
    expect(page.get_by_role("heading", name="Basic Usage")).to_be_visible()
    expect(page.get_by_role("heading", name="Advanced Usage")).to_be_visible()
    expect(page.get_by_role("heading", name="Server & Tooling")).to_be_visible()
    expect(page.get_by_role("heading", name="Examples")).to_be_visible()
    expect(page.get_by_role("heading", name="Migration")).to_be_visible()
    expect(page.get_by_role("heading", name="API Reference")).to_be_visible()


@pytest.mark.e2e
def test_documents_page_title(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents")
    assert page.title() == "Documents - WebComPy Docs"


@pytest.mark.e2e
def test_documents_reload_no_error(docs_page_on, docs_console_messages, assert_no_console_errors):
    page = docs_page_on("/documents")
    page.reload()
    _wait_for_pyscript_init(page, docs_console_messages)


def _contrast_from_rgb_lists(fg: list[float], bg: list[float]) -> float:
    def _lin(channel: float) -> float:
        c = channel / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    l1 = 0.2126 * _lin(fg[0]) + 0.7152 * _lin(fg[1]) + 0.0722 * _lin(fg[2])
    l2 = 0.2126 * _lin(bg[0]) + 0.7152 * _lin(bg[1]) + 0.0722 * _lin(bg[2])
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


@pytest.mark.e2e
def test_disclosure_page_no_overflow_or_toc_overlap_across_viewports(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/basic/disclosure")
    assert page.locator(".prose .prose-table-wrapper").count() > 0

    for width, height in [(390, 844), (1024, 900), (1100, 900), (1280, 900), (1440, 900)]:
        page.set_viewport_size({"width": width, "height": height})
        metrics = page.evaluate(
            "() => {"
            "  const docEl = document.documentElement;"
            "  const prose = document.querySelector('.prose');"
            "  const toc = document.querySelector('.docs-toc');"
            "  const tocStyle = toc ? getComputedStyle(toc) : null;"
            "  const tocVisible = Boolean(toc && tocStyle && tocStyle.display !== 'none');"
            "  const proseRect = prose ? prose.getBoundingClientRect() : null;"
            "  const tocRect = tocVisible ? toc.getBoundingClientRect() : null;"
            "  const wrappers = [...document.querySelectorAll('.prose-table-wrapper')];"
            "  const maxWrapperRight = wrappers.reduce((m, w) => Math.max(m, w.getBoundingClientRect().right), 0);"
            "  return {"
            "    scrollWidth: docEl.scrollWidth,"
            "    clientWidth: docEl.clientWidth,"
            "    tocVisible,"
            "    proseRight: proseRect ? proseRect.right : 0,"
            "    tocLeft: tocRect ? tocRect.left : Infinity,"
            "    maxWrapperRight,"
            "  };"
            "}"
        )
        assert metrics["scrollWidth"] <= metrics["clientWidth"], (
            f"Viewport {width}px overflowed: scrollWidth={metrics['scrollWidth']} > clientWidth={metrics['clientWidth']}"
        )
        if metrics["tocVisible"]:
            assert metrics["proseRight"] <= metrics["tocLeft"] + 1, (
                f"Viewport {width}px prose collided with TOC: proseRight={metrics['proseRight']} > tocLeft={metrics['tocLeft']}"
            )
            assert metrics["maxWrapperRight"] <= metrics["tocLeft"] + 1, (
                f"Viewport {width}px table wrapper collided with TOC: {metrics['maxWrapperRight']} > {metrics['tocLeft']}"
            )


@pytest.mark.e2e
@pytest.mark.parametrize("os_scheme", ["light", "dark"])
def test_theme_form_control_contrast_under_os_and_site_combinations(
    page, docs_page_on, os_scheme, assert_no_console_errors
):
    page.emulate_media(color_scheme=os_scheme)
    docs_page_on("/documents/basic/disclosure")

    toggle = page.locator("button.theme-toggle")
    expect(toggle).to_be_visible()

    for expected_scheme in ("light", "dark"):
        toggle.click()
        page.wait_for_function(
            f"() => (document.querySelector('style[data-webcompy-dynamic=\"0\"]')?.textContent || '').includes('color-scheme: {expected_scheme};')"
        )
        page.evaluate(
            "() => Promise.all("
            "document.getAnimations()"
            ".filter((a) => a.effect && a.effect.getComputedTiming().iterations !== Infinity)"
            ".map((a) => a.finished)"
            ")"
        )
        root_scheme = page.evaluate("() => getComputedStyle(document.documentElement).colorScheme")
        assert expected_scheme in root_scheme

        samples = page.evaluate(
            "() => {"
            "  function parseRgba(str) {"
            "    const m = str.match(/rgba?\\(([^)]+)\\)/);"
            "    if (!m) return [0, 0, 0, 0];"
            "    const parts = m[1].split(',').map((s) => parseFloat(s.trim()));"
            "    return [parts[0], parts[1], parts[2], parts.length > 3 ? parts[3] : 1];"
            "  }"
            "  function composite(fg, bg) {"
            "    const a = fg[3];"
            "    return [fg[0]*a + bg[0]*(1-a), fg[1]*a + bg[1]*(1-a), fg[2]*a + bg[2]*(1-a)];"
            "  }"
            "  function effectiveBg(el) {"
            "    const layers = [];"
            "    let cur = el;"
            "    while (cur) {"
            "      const bg = parseRgba(getComputedStyle(cur).backgroundColor);"
            "      if (bg[3] > 0) layers.push(bg);"
            "      cur = cur.parentElement;"
            "    }"
            "    let base = document.documentElement ? parseRgba(getComputedStyle(document.documentElement).backgroundColor) : [255,255,255,1];"
            "    if (base[3] === 0) base = [255, 255, 255, 1];"
            "    let curRgb = base.slice(0, 3);"
            "    for (let i = layers.length - 1; i >= 0; i--) {"
            "      curRgb = composite(layers[i], curRgb);"
            "    }"
            "    return curRgb;"
            "  }"
            "  const controls = [...document.querySelectorAll('button, input:not([type=\"hidden\"])')];"
            "  return controls"
            "    .filter((el) => el.offsetParent !== null && getComputedStyle(el).visibility !== 'hidden')"
            "    .map((el) => ({"
            "      tag: el.tagName,"
            "      cls: el.className,"
            "      colorScheme: getComputedStyle(el).colorScheme,"
            "      fg: parseRgba(getComputedStyle(el).color).slice(0, 3),"
            "      bg: effectiveBg(el),"
            "    }));"
            "}"
        )
        assert len(samples) > 0
        for sample in samples:
            assert expected_scheme in sample["colorScheme"], f"Control {sample} missing {expected_scheme}"
            ratio = _contrast_from_rgb_lists(sample["fg"], sample["bg"])
            assert ratio >= 4.5, (
                f"Low contrast {ratio:.2f}:1 on {sample['tag']}.{sample['cls']} (os={os_scheme}, site={expected_scheme})"
            )


@pytest.mark.e2e
def test_theme_cookie_reload_has_zero_hydration_mismatches(
    docs_page_on, docs_console_messages, assert_no_console_errors
):
    page = docs_page_on("/documents")
    toggle = page.locator("button.theme-toggle")
    expect(toggle).to_be_visible()

    toggle.click()
    toggle.click()
    page.wait_for_function(
        "() => (document.querySelector('style[data-webcompy-dynamic=\"0\"]')?.textContent || '').includes('color-scheme: dark;')"
    )

    page.reload()
    _wait_for_pyscript_init(page, docs_console_messages)

    page.wait_for_function(
        "() => (document.querySelector('style[data-webcompy-dynamic=\"0\"]')?.textContent || '').includes('color-scheme: dark;')"
    )
    expect(toggle).to_have_attribute("aria-label", "Switch to system theme")
    assert [m for m in docs_console_messages if "Hydration mismatches detected" in m.text] == []
    assert page.locator(".py-error").count() == 0


@pytest.mark.e2e
def test_unknown_route_404_has_zero_hydration_mismatches(docs_page_on, docs_console_messages, assert_no_console_errors):
    page = docs_page_on("/this-page-does-not-exist-404")
    expect(page.get_by_role("heading", name="404 - Not Found")).to_be_visible()
    expect(page.locator(".not-found-path")).to_contain_text("this-page-does-not-exist-404")
    assert [m for m in docs_console_messages if "Hydration mismatches detected" in m.text] == []
    assert page.locator(".py-error").count() == 0


@pytest.mark.e2e
def test_ui_primitives_headless_spinner_visible_and_contrasting(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/basic/ui-primitives")
    spinner = page.locator(".docs-headless-spinner-demo[data-state='loading']")
    expect(spinner).to_be_visible()
    toggle = page.locator("button.theme-toggle")
    for expected_scheme in ("light", "dark"):
        toggle.click()
        page.wait_for_function(
            f"() => (document.querySelector('style[data-webcompy-dynamic=\"0\"]')?.textContent || '').includes('color-scheme: {expected_scheme};')"
        )
        metrics = spinner.evaluate(
            "el => {"
            "  const rect = el.getBoundingClientRect();"
            "  const style = getComputedStyle(el);"
            "  return { width: rect.width, height: rect.height, borderTopColor: style.borderTopColor, borderLeftColor: style.borderLeftColor };"
            "}"
        )
        assert metrics["width"] > 0 and metrics["height"] > 0, f"HeadlessSpinner collapsed: {metrics}"
        assert metrics["borderTopColor"] != "rgba(0, 0, 0, 0)"
        assert metrics["borderLeftColor"] != "rgba(0, 0, 0, 0)"
