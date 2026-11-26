"""Element and signal ownership contracts verified under the real PyScript runtime.

Top-level imports must stay CPython-importable: browser-only modules are
imported inside function bodies (CPython-importability invariant).
"""

from __future__ import annotations

from typing import Any

from webcompy import use_computed, use_reactive_list, use_state
from webcompy.components import ComponentContext, define_component
from webcompy.di import inject
from webcompy.elements.types._element import Element
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, DOM_PORT_KEY
from webcompy.template import render_template


class _BrowserRootHost(Element):
    def _get_belonging_component(self) -> str:
        return ""

    def _get_belonging_components(self) -> tuple[()]:
        return ()


def _active_consumer_count(node: Any) -> int:
    count = 0
    edge = getattr(node, "consumers", None)
    while edge is not None:
        if edge.active:
            count += 1
        edge = edge.next_consumer
    return count


async def test_conditional_repeat_and_text_preserve_caller_computed_in_browser(app, dom_root) -> None:
    refs: dict[str, Any] = {}

    @define_component()
    def BrowserFilteredList(context: ComponentContext[None]):
        query = use_state(lambda: "")
        users = use_reactive_list(lambda: ["Alice", "Bob"])
        filtered = use_computed(
            lambda: [u for u in users.value if query.value.lower() in u.lower()] if query.value else list(users.value)
        )
        refs["query"] = query
        refs["filtered"] = filtered
        return render_template(
            "<div>{% if filtered %}<ul>{% for u in filtered %}<li>{{ u }}</li>{% endfor %}</ul>"
            "<span class='summary'>{{ filtered }}</span>"
            "{% else %}<p>empty</p>{% endif %}</div>",
            {"filtered": filtered},
        )

    scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
    dom_port = inject(DOM_PORT_KEY)
    host = _BrowserRootHost("div")
    host._node_cache = dom_port.query_selector("[data-webcompy-test-root]")
    host._mounted = True

    comp = BrowserFilteredList(None)
    comp._parent = host
    comp._node_idx = 0
    await comp._render()
    await scheduler.await_pending()

    assert "Alice" in str(dom_root.textContent)
    assert "Bob" in str(dom_root.textContent)

    refs["query"].value = "zzz"
    await scheduler.await_pending()
    assert "empty" in str(dom_root.textContent)
    assert refs["filtered"].producers is not None

    refs["query"].value = ""
    await scheduler.await_pending()
    assert refs["filtered"].value == ["Alice", "Bob"]
    assert "Alice" in str(dom_root.textContent)
    assert "Bob" in str(dom_root.textContent)

    refs["query"].value = "Bob"
    await scheduler.await_pending()
    assert "Bob" in str(dom_root.textContent)
    assert "Alice" not in str(dom_root.textContent)

    comp._remove_element()
    assert refs["filtered"].producers is not None


async def test_framework_owned_template_computed_cleans_up_in_browser(app, dom_root) -> None:
    refs: dict[str, Any] = {}

    @define_component()
    def OwnedCleanupCheck(context: ComponentContext[None]):
        show = use_state(lambda: True)
        count = use_state(lambda: 3)
        refs["show"] = show
        refs["count"] = count
        return render_template(
            "<div>{% if show %}<span class='c-{{ count }}'>{{ count + 1 }}</span>{% endif %}</div>",
            {"show": show, "count": count},
        )

    scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
    dom_port = inject(DOM_PORT_KEY)
    host = _BrowserRootHost("div")
    host._node_cache = dom_port.query_selector("[data-webcompy-test-root]")
    host._mounted = True

    comp = OwnedCleanupCheck(None)
    comp._parent = host
    comp._node_idx = 0
    await comp._render()
    await scheduler.await_pending()

    assert "4" in str(dom_root.textContent)
    assert _active_consumer_count(refs["count"]) == 2

    refs["show"].value = False
    await scheduler.await_pending()
    assert _active_consumer_count(refs["count"]) == 0

    comp._remove_element()
