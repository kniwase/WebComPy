import itertools

import pytest
from playwright.sync_api import expect

from e2e.docs.conftest import _wait_for_demo_iframe, _wait_for_pyscript_init


@pytest.mark.e2e
def test_navbar_dropdown_items_have_no_layout_shift_before_hydration(
    page, docs_server_url, docs_console_messages, assert_no_console_errors
):
    page.goto(docs_server_url, wait_until="domcontentloaded")
    heights = page.evaluate(
        "() => {"
        "  const home = document.querySelector('li.navbar-item');"
        "  const dropdowns = [...document.querySelectorAll('li.navbar-item-dropdown')];"
        "  const anchors = (li) => {"
        "    const walker = document.createTreeWalker(li, NodeFilter.SHOW_COMMENT);"
        "    let count = 0;"
        "    while (walker.nextNode()) {"
        "      if (walker.currentNode.data === 'webcompy-teleport-anchor') count += 1;"
        "    }"
        "    return count;"
        "  };"
        "  return {"
        "    home: home ? home.offsetHeight : null,"
        "    dropdowns: dropdowns.map(li => {"
        "      const trigger = li.querySelector('button');"
        "      return {li: li.offsetHeight, trigger: trigger ? trigger.offsetHeight : null, anchors: anchors(li)};"
        "    }),"
        "  };"
        "}"
    )
    assert heights["home"] is not None
    assert heights["dropdowns"], "expected at least one dropdown item"
    for d in heights["dropdowns"]:
        assert d["anchors"] == 1
        assert d["li"] == heights["home"]
        assert d["trigger"] is not None and d["li"] == d["trigger"]
    _wait_for_pyscript_init(page, docs_console_messages)


@pytest.mark.e2e
def test_navbar_dropdown_opens_and_closes_cleanly(docs_app_page, assert_no_console_errors):
    page = docs_app_page
    triggers = page.locator("li.navbar-item-dropdown button")
    expect(triggers).to_have_count(1)
    expect(page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Demos")).to_have_count(0)
    docs_toggle = triggers.first
    docs_toggle.click()
    expect(docs_toggle).to_have_attribute("aria-expanded", "true")
    expect(page.locator("ul.navbar-dropdown:not([hidden])")).to_have_count(1)
    page.locator(".navbar-brand").click()
    expect(docs_toggle).to_have_attribute("aria-expanded", "false")
    expect(page.locator("ul.navbar-dropdown:not([hidden])")).to_have_count(0)


@pytest.mark.e2e
def test_home_page_heading(docs_app_page, assert_no_console_errors):
    heading = docs_app_page.get_by_role("heading", name="Build Frontend in Python", level=1)
    expect(heading).to_be_visible()


@pytest.mark.e2e
def test_home_hero_get_started_link(docs_app_page, assert_no_console_errors):
    link = docs_app_page.get_by_role("link", name="Get Started")
    expect(link).to_be_visible()
    assert link.get_attribute("href") == "/documents/getting-started/what-is-webcompy/"


@pytest.mark.e2e
def test_home_hero_navigates_to_getting_started(docs_app_page, assert_no_console_errors):
    docs_app_page.evaluate("window.__home_spa_marker = 1")
    docs_app_page.get_by_role("link", name="Get Started").click()
    assert "/documents/getting-started/what-is-webcompy" in docs_app_page.url
    expect(docs_app_page.locator("article.prose h1#what-is-webcompy")).to_be_visible()
    assert docs_app_page.evaluate("window.__home_spa_marker") == 1


@pytest.mark.e2e
def test_home_has_no_duplicated_installation_content(docs_app_page, assert_no_console_errors):
    expect(docs_app_page.get_by_text("Get started with Poetry")).to_have_count(0)
    expect(docs_app_page.locator(".commands-table")).to_have_count(0)


@pytest.mark.e2e
def test_home_code_block_vertical_margins_are_symmetric(docs_app_page, assert_no_console_errors):
    block = docs_app_page.locator("pre.code-block").first
    expect(block).to_be_visible()
    margins = block.evaluate("el => [getComputedStyle(el).marginTop, getComputedStyle(el).marginBottom]")
    assert margins[0] == margins[1], f"code block margins must be symmetric, got {margins}"
    assert margins[0] != "0px", f"code block margins must be non-zero, got {margins}"


@pytest.mark.e2e
def test_home_page_title(docs_app_page, assert_no_console_errors):
    assert docs_app_page.title() == "WebComPy - Python Frontend Framework"


@pytest.mark.e2e
def test_documents_index_card_scoped_margin(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents")
    card = page.locator(".ui-card").first
    expect(card).to_be_visible()
    margin_top = card.evaluate("el => parseFloat(getComputedStyle(el).marginTop)")
    assert margin_top > 0


@pytest.mark.e2e
def test_home_spa_navigation_to_helloworld(docs_app_page, assert_no_console_errors):
    dropdown_toggle = docs_app_page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Documents")
    dropdown_toggle.click()
    helloworld_link = docs_app_page.get_by_role("menuitem", name="Hello World")
    helloworld_link.scroll_into_view_if_needed()
    helloworld_link.click()
    assert "/documents/examples/hello-world" in docs_app_page.url
    expect(docs_app_page.locator("article.prose h1")).to_have_text("Hello World")
    frame = _wait_for_demo_iframe(docs_app_page, "helloworld")
    heading = frame.get_by_role("heading", name="Hello WebComPy!")
    expect(heading).to_be_visible()


@pytest.mark.e2e
def test_home_spa_navigation_back_from_helloworld(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/examples/hello-world")
    home_link = page.locator("nav .navbar-list a[href='/']")
    home_link.click()
    assert page.url.endswith("/") or page.url == page.url.rstrip("/") + "/"
    heading = page.get_by_role("heading", name="Build Frontend in Python", level=1)
    expect(heading).to_be_visible()


@pytest.mark.e2e
def test_home_reload_no_error(docs_app_page, docs_console_messages, assert_no_console_errors):
    docs_app_page.reload()
    _wait_for_pyscript_init(docs_app_page, docs_console_messages)


@pytest.mark.e2e
def test_home_dropdown_anchored_to_trigger_on_scroll(docs_app_page, assert_no_console_errors):
    dropdown_toggle = docs_app_page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Documents")
    dropdown_toggle.click()
    dropdown = docs_app_page.locator("ul.navbar-dropdown").filter(has_text="Hello World")
    expect(dropdown).to_be_visible()

    def anchored():
        return docs_app_page.wait_for_function(
            "() => {"
            "  const menu = document.querySelector('ul.navbar-dropdown:not([hidden])');"
            "  const toggle = [...document.querySelectorAll('.navbar-dropdown-toggle')]"
            "    .find(t => t.getAttribute('aria-expanded') === 'true');"
            "  if (!menu || !toggle) return false;"
            "  return Math.abs(menu.getBoundingClientRect().y - toggle.getBoundingClientRect().bottom) < 2;"
            "}",
            timeout=5000,
        )

    anchored()
    docs_app_page.evaluate("window.scrollTo(0, 200)")
    expect(dropdown).to_be_visible()
    anchored()
    docs_app_page.evaluate("window.scrollTo(0, 0)")


@pytest.mark.e2e
def test_home_dropdown_stays_within_viewport_after_resize(docs_app_page, assert_no_console_errors):
    dropdown_toggle = docs_app_page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Documents")
    dropdown_toggle.click()
    dropdown = docs_app_page.locator("ul.navbar-dropdown").filter(has_text="Hello World")
    expect(dropdown).to_be_visible()
    docs_app_page.set_viewport_size({"width": 1000, "height": 800})
    docs_app_page.wait_for_function(
        "() => {"
        "  const menu = document.querySelector('ul.navbar-dropdown:not([hidden])');"
        "  if (!menu) return false;"
        "  const rect = menu.getBoundingClientRect();"
        "  return rect.width > 0 && rect.left >= 0 && rect.right <= window.innerWidth && rect.top >= 0;"
        "}",
        timeout=5000,
    )


@pytest.mark.e2e
def test_home_mobile_dropdown_nested_below_trigger(docs_app_page, assert_no_console_errors):
    docs_app_page.set_viewport_size({"width": 600, "height": 800})
    docs_app_page.locator("button.navbar-mobile-toggle").click()
    dropdown_toggle = docs_app_page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Documents")
    dropdown_toggle.click()
    dropdown = docs_app_page.locator("ul.navbar-dropdown").filter(has_text="Hello World")
    expect(dropdown).to_be_visible()
    menu_id = dropdown.get_attribute("id")
    assert menu_id is not None
    assert (
        docs_app_page.evaluate("menuId => getComputedStyle(document.getElementById(menuId)).position", menu_id)
        == "fixed"
    )
    docs_app_page.wait_for_function(
        "() => {"
        "  const menu = document.querySelector('ul.navbar-dropdown:not([hidden])');"
        "  const toggle = [...document.querySelectorAll('.navbar-dropdown-toggle')]"
        "    .find(t => t.getAttribute('aria-expanded') === 'true');"
        "  if (!menu || !toggle) return false;"
        "  return Math.abs(menu.getBoundingClientRect().y - toggle.getBoundingClientRect().bottom) < 2;"
        "}",
        timeout=5000,
    )
    trigger_box = dropdown_toggle.bounding_box()
    box = dropdown.bounding_box()
    assert box is not None and trigger_box is not None
    strip_padding = 24
    assert abs(box["x"] - strip_padding) < 2
    assert abs((box["x"] + box["width"]) - (trigger_box["x"] + trigger_box["width"])) < 2
    home_link = docs_app_page.locator("li.navbar-item a").filter(has_text="Home")
    expect(home_link).to_be_visible()
    hit = docs_app_page.evaluate(
        "() => {"
        "  const el = document.querySelector('li.navbar-item a');"
        "  const r = el.getBoundingClientRect();"
        "  const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);"
        "  return hit ? (hit.closest('.navbar-list') ? 'strip' : hit.tagName) : null;"
        "}"
    )
    assert hit == "strip"


@pytest.mark.e2e
def test_home_dropdown_stays_within_viewport_at_mid_width(docs_app_page, assert_no_console_errors):
    docs_app_page.set_viewport_size({"width": 1024, "height": 800})
    dropdown_toggle = docs_app_page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Documents")
    dropdown_toggle.click()
    dropdown = docs_app_page.locator("ul.navbar-dropdown").filter(has_text="Hello World")
    expect(dropdown).to_be_visible()
    docs_app_page.wait_for_function(
        "() => {"
        "  const menu = document.querySelector('ul.navbar-dropdown:not([hidden])');"
        "  if (!menu) return false;"
        "  const rect = menu.getBoundingClientRect();"
        "  return rect.width > 0 && rect.left >= 0 && rect.right <= window.innerWidth;"
        "}",
        timeout=5000,
    )


@pytest.mark.e2e
def test_navbar_dropdown_links_crawlable_in_initial_html(
    page, docs_server_url, docs_console_messages, assert_no_console_errors
):
    page.goto(docs_server_url, wait_until="domcontentloaded")
    content = page.content()
    assert "wc-teleport-block:" in content
    assert "/documents/" in content
    assert "/documents/examples/teleport/" in content
    dropdown_links = page.locator("body > ul[role='menu'] a").count()
    assert dropdown_links > 0
    _wait_for_pyscript_init(page, docs_console_messages)
    leftover = page.evaluate(
        "() => [...document.body.childNodes].filter("
        "n => n.nodeType === 8 && n.data.startsWith('wc-teleport-block')).length"
    )
    assert leftover == 0


@pytest.mark.e2e
def test_navbar_brand_is_home_link_and_navigates(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/documents/getting-started/what-is-webcompy")
    brand = page.locator("nav a.navbar-brand")
    expect(brand).to_be_visible()
    expect(brand).to_have_attribute("href", "/")
    brand.click()
    expect(page.get_by_role("heading", name="Build Frontend in Python", level=1)).to_be_visible()


@pytest.mark.e2e
def test_navbar_dropdown_grouped_and_scrollable(docs_app_page, assert_no_console_errors):
    docs_toggle = docs_app_page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Documents")
    docs_toggle.click()
    dropdown = docs_app_page.locator("ul.navbar-dropdown:not([hidden])")
    expect(dropdown).to_be_visible()
    sections = [text.strip() for text in dropdown.locator("li.navbar-dropdown-section").all_text_contents()]
    assert "Getting Started" in sections
    assert "Guides" in sections
    assert "API Reference" in sections
    metrics = dropdown.evaluate(
        "el => ({ ch: el.clientHeight, sh: el.scrollHeight, oy: getComputedStyle(el).overflowY })"
    )
    assert metrics["ch"] <= 525
    assert metrics["sh"] > metrics["ch"]
    assert metrics["oy"] in ("auto", "scroll")


@pytest.mark.e2e
def test_home_feature_cards_balanced_and_zero_card_margin(docs_app_page, assert_no_console_errors):
    cards = docs_app_page.locator(".feature-cards .ui-card")
    expect(cards).to_have_count(6)
    for width, expected_cols in [(1280, 3), (900, 2), (390, 1)]:
        docs_app_page.set_viewport_size({"width": width, "height": 900})
        metrics = docs_app_page.evaluate(
            "() => {"
            "  const cards = [...document.querySelectorAll('.feature-cards .ui-card')];"
            "  return {"
            "    scrollWidth: document.documentElement.scrollWidth,"
            "    clientWidth: document.documentElement.clientWidth,"
            "    boxes: cards.map(c => {"
            "      const r = c.getBoundingClientRect();"
            "      return { top: Math.round(r.top), left: Math.round(r.left), marginTop: getComputedStyle(c).marginTop };"
            "    }),"
            "  };"
            "}"
        )
        assert metrics["scrollWidth"] <= metrics["clientWidth"]
        assert all(b["marginTop"] == "0px" for b in metrics["boxes"])
        first_row_tops = {b["top"] for b in metrics["boxes"][:expected_cols]}
        assert len(first_row_tops) == 1


@pytest.mark.e2e
def test_root_accessibility_semantics(docs_app_page, assert_no_console_errors):
    info = docs_app_page.evaluate(
        "() => {"
        "  const htmlLang = document.documentElement.getAttribute('lang');"
        "  const skip = document.querySelector('a.skip-link');"
        "  const main = document.querySelector('main#main-content');"
        "  const primaryNav = document.querySelector('nav[aria-label=\"Primary navigation\"]');"
        "  const toggle = document.querySelector('button.theme-toggle');"
        "  const headings = [...document.querySelectorAll('main h1, main h2, main h3, main h4, main h5, main h6')]"
        "    .map(h => parseInt(h.tagName.slice(1), 10));"
        "  return {"
        "    htmlLang,"
        "    skipHref: skip ? skip.getAttribute('href') : null,"
        "    hasMain: !!main,"
        "    hasPrimaryNav: !!primaryNav,"
        "    toggleRole: toggle ? toggle.getAttribute('role') : 'missing',"
        "    hasToggleSvg: toggle ? !!toggle.querySelector('svg') : false,"
        "    headings,"
        "  };"
        "}"
    )
    assert info["htmlLang"] == "en"
    assert info["skipHref"] == "/#main-content"
    assert info["hasMain"] is True
    assert info["hasPrimaryNav"] is True
    assert info["toggleRole"] is None
    assert info["hasToggleSvg"] is True
    assert info["headings"][0] == 1
    for prev, nxt in itertools.pairwise(info["headings"]):
        assert nxt <= prev + 1, f"Skipped heading level on Home: {info['headings']}"
