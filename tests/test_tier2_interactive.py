import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "tests" / "e2e"))

from webcompy.ports._server._virtual_dom import VirtualDOMEvent
from webcompy.testing import TestRenderer


def test_switch_toggle():
    from my_app.pages.switch_test import SwitchPage

    result = TestRenderer.render(SwitchPage)
    assert "switch-on" in result.to_html()
    assert "switch-off" not in result.to_html()

    btn = result.find_by_attribute("data-testid", "toggle-btn")
    assert btn is not None
    btn.dispatchEvent(VirtualDOMEvent("click"))

    assert "switch-off" in result.to_html()
    assert "switch-on" not in result.to_html()


def test_switch_toggle_back():
    from my_app.pages.switch_test import SwitchPage

    result = TestRenderer.render(SwitchPage)
    btn = result.find_by_attribute("data-testid", "toggle-btn")
    btn.dispatchEvent(VirtualDOMEvent("click"))
    assert "switch-off" in result.to_html()

    btn = result.find_by_attribute("data-testid", "toggle-btn")
    btn.dispatchEvent(VirtualDOMEvent("click"))
    assert "switch-on" in result.to_html()


def test_reactive_signal():
    from my_app.pages.signal import ReactivePage

    result = TestRenderer.render(ReactivePage)
    count_el = result.find_by_attribute("data-testid", "count")
    assert count_el is not None
    assert count_el.textContent == "0"
    btn = result.find_by_attribute("data-testid", "increment-btn")
    btn.dispatchEvent(VirtualDOMEvent("click"))
    assert count_el.textContent == "1"


def test_reactive_computed():
    from my_app.pages.signal import ReactivePage

    result = TestRenderer.render(ReactivePage)
    doubled_el = result.find_by_attribute("data-testid", "doubled")
    assert doubled_el is not None
    assert doubled_el.textContent == "0"
    btn = result.find_by_attribute("data-testid", "increment-btn")
    btn.dispatchEvent(VirtualDOMEvent("click"))
    assert doubled_el.textContent == "2"


def test_repeat_add_items():
    from my_app.pages.repeat import RepeatPage

    result = TestRenderer.render(RepeatPage)
    assert "<li" not in result.to_html()

    btn = result.find_by_attribute("data-testid", "add-btn")
    btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 1

    btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 2


def test_repeat_remove_items():
    from my_app.pages.repeat import RepeatPage

    result = TestRenderer.render(RepeatPage)
    btn = result.find_by_attribute("data-testid", "add-btn")
    for _ in range(3):
        btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 3

    btn_remove = result.find_by_attribute("data-testid", "remove-btn")
    btn_remove.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 2

    btn_remove.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 1

    btn_remove.dispatchEvent(VirtualDOMEvent("click"))
    assert "<li" not in result.to_html()


def test_keyed_repeat_add_items():
    from my_app.pages.keyed_repeat import KeyedRepeatPage

    result = TestRenderer.render(KeyedRepeatPage)
    assert "<li" not in result.to_html()

    btn = result.find_by_attribute("data-testid", "keyed-add-btn")
    btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 1

    btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 2


@pytest.mark.skip(reason="re-rendering creates new component instance, resetting signals")
def test_keyed_repeat_remove_first():
    from my_app.pages.keyed_repeat import KeyedRepeatPage

    result = TestRenderer.render(KeyedRepeatPage)
    btn = result.find_by_attribute("data-testid", "keyed-add-btn")
    for _ in range(3):
        btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 3

    btn_remove = result.find_by_attribute("data-testid", "keyed-remove-first-btn")
    btn_remove.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 2


@pytest.mark.skip(reason="re-rendering creates new component instance, resetting signals")
def test_keyed_repeat_insert_at_start():
    from my_app.pages.keyed_repeat import KeyedRepeatPage

    result = TestRenderer.render(KeyedRepeatPage)
    btn = result.find_by_attribute("data-testid", "keyed-add-btn")
    for _ in range(2):
        btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 2

    btn_insert = result.find_by_attribute("data-testid", "keyed-add-start-btn")
    btn_insert.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 3


def test_dict_repeat_add_items():
    from my_app.pages.dict_repeat import DictRepeatPage

    result = TestRenderer.render(DictRepeatPage)
    assert "<li" not in result.to_html()

    btn = result.find_by_attribute("data-testid", "dict-add-btn")
    btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 1

    btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 2


def test_dict_repeat_remove_first():
    from my_app.pages.dict_repeat import DictRepeatPage

    result = TestRenderer.render(DictRepeatPage)
    btn = result.find_by_attribute("data-testid", "dict-add-btn")
    for _ in range(3):
        btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 3

    btn_remove = result.find_by_attribute("data-testid", "dict-remove-first-btn")
    btn_remove.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 2


def test_dict_repeat_clear():
    from my_app.pages.dict_repeat import DictRepeatPage

    result = TestRenderer.render(DictRepeatPage)
    btn = result.find_by_attribute("data-testid", "dict-add-btn")
    for _ in range(2):
        btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("<li") == 2

    btn_clear = result.find_by_attribute("data-testid", "dict-clear-btn")
    btn_clear.dispatchEvent(VirtualDOMEvent("click"))
    assert "<li" not in result.to_html()


def test_nested_dynamic_initial_list():
    from my_app.pages.nested_dynamic import NestedDynamicPage

    result = TestRenderer.render(NestedDynamicPage)
    assert "list-view" in result.to_html()
    assert "grid-view" not in result.to_html()
    assert result.to_html().count("list-item") == 3


def test_nested_dynamic_switch_to_grid():
    from my_app.pages.nested_dynamic import NestedDynamicPage

    result = TestRenderer.render(NestedDynamicPage)
    btn = result.find_by_attribute("data-testid", "grid-btn")
    btn.dispatchEvent(VirtualDOMEvent("click"))
    assert "grid-view" in result.to_html()
    assert "list-view" not in result.to_html()
    assert result.to_html().count("grid-item") == 3


def test_nested_dynamic_switch_back():
    from my_app.pages.nested_dynamic import NestedDynamicPage

    result = TestRenderer.render(NestedDynamicPage)
    grid_btn = result.find_by_attribute("data-testid", "grid-btn")
    grid_btn.dispatchEvent(VirtualDOMEvent("click"))
    assert "grid-view" in result.to_html()

    list_btn = result.find_by_attribute("data-testid", "list-btn")
    list_btn.dispatchEvent(VirtualDOMEvent("click"))
    assert "list-view" in result.to_html()
    assert "grid-view" not in result.to_html()
    assert result.to_html().count("list-item") == 3


def test_nested_dynamic_add_item():
    from my_app.pages.nested_dynamic import NestedDynamicPage

    result = TestRenderer.render(NestedDynamicPage)
    assert result.to_html().count("list-item") == 3

    btn = result.find_by_attribute("data-testid", "add-item-btn")
    btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("list-item") == 4


def test_nested_dynamic_add_then_switch():
    from my_app.pages.nested_dynamic import NestedDynamicPage

    result = TestRenderer.render(NestedDynamicPage)
    add_btn = result.find_by_attribute("data-testid", "add-item-btn")
    add_btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("list-item") == 4

    grid_btn = result.find_by_attribute("data-testid", "grid-btn")
    grid_btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("grid-item") == 4


def test_nested_dynamic_remove_first():
    from my_app.pages.nested_dynamic import NestedDynamicPage

    result = TestRenderer.render(NestedDynamicPage)
    assert result.to_html().count("list-item") == 3

    btn = result.find_by_attribute("data-testid", "remove-first-btn")
    btn.dispatchEvent(VirtualDOMEvent("click"))
    assert result.to_html().count("list-item") == 2


def test_di_provide_inject_from_parent():
    from my_app.pages.di_test import DiProviderWrapper

    result = TestRenderer.render(DiProviderWrapper)
    assert "dark-theme" in result.to_html()

    child = result.find_by_attribute("data-testid", "child-theme")
    assert child is not None
    assert child.textContent == "dark-theme"


@pytest.mark.skip(reason="app.provide() happens after init, but component renders during init")
def test_di_inject_from_app_level():
    from my_app.keys import AppThemeKey
    from my_app.pages.di_test import DiInjectPage

    from webcompy.app import WebComPyApp, WebComPyAppConfig
    from webcompy.testing import TestRenderer

    app = WebComPyApp(root_component=DiInjectPage, config=WebComPyAppConfig(base_url="/"))
    app._di_scope.provide(AppThemeKey, "app-dark-theme")
    result = TestRenderer.render(DiInjectPage)
    assert "app-dark-theme" in result.to_html()


def test_reactive_list_operations():
    from my_app.pages.signal import ReactivePage

    result = TestRenderer.render(ReactivePage)
    list_count = result.find_by_attribute("data-testid", "list-count")
    assert list_count is not None
    assert list_count.textContent == "3"

    add_btn = result.find_by_attribute("data-testid", "list-add-btn")
    add_btn.dispatchEvent(VirtualDOMEvent("click"))
    assert list_count.textContent == "4"

    remove_btn = result.find_by_attribute("data-testid", "list-remove-btn")
    remove_btn.dispatchEvent(VirtualDOMEvent("click"))
    assert list_count.textContent == "3"


def test_reactive_dict_operations():
    from my_app.pages.signal import ReactivePage

    result = TestRenderer.render(ReactivePage)
    dict_count = result.find_by_attribute("data-testid", "dict-count")
    assert dict_count is not None
    assert dict_count.textContent == "1"

    add_btn = result.find_by_attribute("data-testid", "dict-add-btn")
    add_btn.dispatchEvent(VirtualDOMEvent("click"))
    assert dict_count.textContent == "2"


def test_scoped_style_attribute_selector():
    from my_app.pages.scoped_style import ScopedStylePage

    style_content = ScopedStylePage.scoped_style
    assert "webcompy-cid-" in style_content


def test_scoped_style_top_level_media_query():
    from my_app.pages.scoped_style import ScopedStylePage

    style_content = ScopedStylePage.scoped_style
    assert "top-level-media-text" in style_content
    assert "webcompy-cid-" in style_content
    assert any(token in style_content.replace(" ", "") for token in ("@media(max-width:", "@media (max-width:"))
    assert "@media[webcompy-cid-" not in style_content


def test_lifecycle_hooks_fire():
    from my_app.pages.lifecycle import LifecyclePage

    result = TestRenderer.render(LifecyclePage)
    render_count = result.find_by_attribute("data-testid", "render-count")
    assert render_count is not None
    assert render_count.textContent == "1"
