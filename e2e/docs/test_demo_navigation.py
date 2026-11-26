import pytest
from playwright.sync_api import expect

HELLOWORLD_MARKER = "HelloWorld"
TODO_MARKER = "TodoApp"


@pytest.mark.e2e
def test_initial_load_restores_code_without_main_frame_refetch(docs_page_on, page):
    requests: list[str] = []

    def _on_request(req):
        if req.frame == page.main_frame and "/_demos/helloworld/app.py" in req.url:
            requests.append(req.url)

    page.on("request", _on_request)
    docs_page_on("/documents/examples/hello-world")
    expect(page.locator(".demo-display-root .code-block")).to_contain_text(HELLOWORLD_MARKER)
    page.wait_for_timeout(1500)
    page.remove_listener("request", _on_request)
    assert not requests, f"code was refetched from the main frame: {requests}"


@pytest.mark.e2e
def test_spa_navigation_updates_code_and_fetches_new_source(docs_page_on, page):
    docs_page_on("/documents/examples/hello-world")
    code_block = page.locator(".demo-display-root .code-block")
    expect(code_block).to_contain_text(HELLOWORLD_MARKER)

    requests: list[str] = []

    def _on_request(req):
        if req.frame == page.main_frame and "/_demos/todo/app.py" in req.url:
            requests.append(req.url)

    page.on("request", _on_request)
    page.locator('.docs-sidebar a[href="/documents/examples/todo/"]').first.click()

    expect(page.locator(".demo-display-title")).to_have_text("ToDo List")
    expect(code_block).to_contain_text(TODO_MARKER)
    page.remove_listener("request", _on_request)
    assert requests, "expected a main-frame fetch of /_demos/todo/app.py after navigation"


@pytest.mark.e2e
def test_removed_sample_route_renders_404(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/todo")
    expect(page.get_by_role("heading", name="404 - Not Found")).to_be_visible()
    expect(page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Demos")).to_have_count(0)


def _contrast_ratio(fg: list[float], bg: list[float]) -> float:
    def _lin(channel: float) -> float:
        c = channel / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    l1 = 0.2126 * _lin(fg[0]) + 0.7152 * _lin(fg[1]) + 0.0722 * _lin(fg[2])
    l2 = 0.2126 * _lin(bg[0]) + 0.7152 * _lin(bg[1]) + 0.0722 * _lin(bg[2])
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


@pytest.mark.e2e
@pytest.mark.parametrize("os_scheme", ["light", "dark"])
def test_demo_iframe_live_theme_sync_and_contrast(page, docs_page_on, os_scheme, assert_no_console_errors):
    from e2e.docs.conftest import _wait_for_demo_iframe

    page.emulate_media(color_scheme=os_scheme)
    docs_page_on("/documents/examples/todo")
    frame = _wait_for_demo_iframe(page, "todo")
    frame.evaluate("window.__demo_sentinel = 1")

    toggle = page.locator("button.theme-toggle")
    expect(toggle).to_be_visible()

    for expected_scheme in ("light", "dark"):
        toggle.click()
        page.wait_for_function(
            f"() => (document.querySelector('style[data-webcompy-dynamic=\"0\"]')?.textContent || '').includes('color-scheme: {expected_scheme};')"
        )
        frame.wait_for_function(
            f"() => (document.querySelector('style[data-webcompy-dynamic=\"0\"]')?.textContent || '').includes('color-scheme: {expected_scheme};')"
        )
        page.evaluate(
            "() => Promise.all("
            "document.getAnimations()"
            ".filter((a) => a.effect && a.effect.getComputedTiming().iterations !== Infinity)"
            ".map((a) => a.finished)"
            ")"
        )
        frame.evaluate(
            "() => Promise.all("
            "document.getAnimations()"
            ".filter((a) => a.effect && a.effect.getComputedTiming().iterations !== Infinity)"
            ".map((a) => a.finished)"
            ")"
        )
        assert frame.evaluate("window.__demo_sentinel") == 1
        samples = frame.evaluate(
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
            "    let curRgb = [255, 255, 255];"
            "    for (let i = layers.length - 1; i >= 0; i--) {"
            "      curRgb = composite(layers[i], curRgb);"
            "    }"
            "    return curRgb;"
            "  }"
            '  const els = [...document.querySelectorAll(\'#webcompy-app button, #webcompy-app input:not([type="checkbox"]):not([type="hidden"]), #webcompy-app li span\')];'
            "  return els.map((el) => ({"
            "    tag: el.tagName,"
            "    text: (el.textContent || '').trim(),"
            "    colorScheme: getComputedStyle(el).colorScheme,"
            "    fg: parseRgba(getComputedStyle(el).color).slice(0, 3),"
            "    bg: effectiveBg(el),"
            "  }));"
            "}"
        )
        assert len(samples) > 0
        for sample in samples:
            assert expected_scheme in sample["colorScheme"], f"Iframe control missing {expected_scheme}: {sample}"
            ratio = _contrast_ratio(sample["fg"], sample["bg"])
            assert ratio >= 4.5, (
                f"Low iframe contrast {ratio:.2f}:1 on {sample} (os={os_scheme}, site={expected_scheme})"
            )


@pytest.mark.e2e
def test_standard_html_standalone_fallback_no_errors(page, docs_server_url, docs_console_messages):
    page_errors: list[object] = []
    page.on("pageerror", lambda err: page_errors.append(err))
    page.add_init_script("document.cookie = 'webcompy-theme=dark; Path=/';")
    page.goto(f"{docs_server_url}_demos/standard.html?app=helloworld")
    page.wait_for_function(
        "() => (document.querySelector('style[data-webcompy-dynamic=\"0\"]')?.textContent || '').includes('color-scheme: dark;')"
    )
    assert "dark" in page.evaluate("() => getComputedStyle(document.documentElement).colorScheme")
    assert page_errors == []
    assert [m for m in docs_console_messages if m.type == "error"] == []
