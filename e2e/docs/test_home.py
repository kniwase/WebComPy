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
def test_navbar_dropdown_opens_and_switches_exclusively(docs_app_page, assert_no_console_errors):
    page = docs_app_page
    triggers = page.locator("li.navbar-item-dropdown button")
    first = triggers.nth(0)
    second = triggers.nth(1)
    first.click()
    expect(first).to_have_attribute("aria-expanded", "true")
    expect(page.locator("ul.navbar-dropdown:not([hidden])")).to_have_count(1)
    # Activating the sibling dropdown closes the open menu (mutual exclusivity)
    second.click()
    expect(second).to_have_attribute("aria-expanded", "true")
    expect(first).to_have_attribute("aria-expanded", "false")
    expect(page.locator("ul.navbar-dropdown:not([hidden])")).to_have_count(1)
    # Instance DOM ids are unique
    ids = page.evaluate("() => [...document.querySelectorAll('li.navbar-item-dropdown button')].map((b) => b.id)")
    assert ids[0] != ids[1]
    # Outside click closes the menu
    page.locator(".navbar-brand").click()
    expect(page.locator("ul.navbar-dropdown:not([hidden])")).to_have_count(0)


@pytest.mark.e2e
def test_home_page_heading(docs_app_page, assert_no_console_errors):
    heading = docs_app_page.get_by_role("heading", name="What is WebComPy")
    expect(heading).to_be_visible()


@pytest.mark.e2e
def test_home_page_title(docs_app_page, assert_no_console_errors):
    assert docs_app_page.title() == "WebComPy - Python Frontend Framework"


@pytest.mark.e2e
def test_home_spa_navigation_to_helloworld(docs_app_page, assert_no_console_errors):
    dropdown_toggle = docs_app_page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Demos")
    dropdown_toggle.click()
    helloworld_link = docs_app_page.get_by_role("menuitem", name="HelloWorld")
    helloworld_link.click()
    assert "/sample/helloworld" in docs_app_page.url
    frame = _wait_for_demo_iframe(docs_app_page, "helloworld")
    heading = frame.get_by_role("heading", name="Hello WebComPy!")
    expect(heading).to_be_visible()


@pytest.mark.e2e
def test_home_spa_navigation_back_from_helloworld(docs_page_on, assert_no_console_errors):
    page = docs_page_on("/sample/helloworld")
    home_link = page.locator("nav a[href='/']")
    home_link.click()
    assert page.url.endswith("/") or page.url == page.url.rstrip("/") + "/"
    heading = page.get_by_role("heading", name="What is WebComPy")
    expect(heading).to_be_visible()


@pytest.mark.e2e
def test_home_reload_no_error(docs_app_page, docs_console_messages, assert_no_console_errors):
    docs_app_page.reload()
    _wait_for_pyscript_init(docs_app_page, docs_console_messages)


@pytest.mark.e2e
def test_home_dropdown_anchored_to_trigger_on_scroll(docs_app_page, assert_no_console_errors):
    dropdown_toggle = docs_app_page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Demos")
    dropdown_toggle.click()
    dropdown = docs_app_page.locator("ul.navbar-dropdown").filter(has_text="HelloWorld")
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
    dropdown_toggle = docs_app_page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Demos")
    dropdown_toggle.click()
    dropdown = docs_app_page.locator("ul.navbar-dropdown").filter(has_text="HelloWorld")
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
    dropdown_toggle = docs_app_page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Demos")
    dropdown_toggle.click()
    dropdown = docs_app_page.locator("ul.navbar-dropdown").filter(has_text="HelloWorld")
    expect(dropdown).to_be_visible()
    menu_id = dropdown.get_attribute("id")
    assert menu_id is not None
    assert (
        docs_app_page.evaluate("menuId => getComputedStyle(document.getElementById(menuId)).position", menu_id)
        == "fixed"
    )
    # The menu is anchored below the trigger (nested-expansion look)
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
    # The menu spans the strip width: left edge at the strip padding,
    # right edge on the trigger's right edge (anchored, full-width)
    strip_padding = 24
    assert abs(box["x"] - strip_padding) < 2
    assert abs((box["x"] + box["width"]) - (trigger_box["x"] + trigger_box["width"])) < 2
    # The expanded strip stays visible and interactive above the menu
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
    dropdown_toggle = docs_app_page.locator("nav li button[aria-haspopup='menu']").filter(has_text="Demos")
    dropdown_toggle.click()
    dropdown = docs_app_page.locator("ul.navbar-dropdown").filter(has_text="HelloWorld")
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
    assert "/sample/teleport/" in content
    dropdown_links = page.locator("body > ul[role='menu'] a").count()
    assert dropdown_links > 0
    _wait_for_pyscript_init(page, docs_console_messages)
    leftover = page.evaluate(
        "() => [...document.body.childNodes].filter("
        "n => n.nodeType === 8 && n.data.startsWith('wc-teleport-block')).length"
    )
    assert leftover == 0
