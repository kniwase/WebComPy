from __future__ import annotations

import asyncio
import warnings

import pytest

from tests.test_hydration_preservation_helpers import (
    make_prerendered_parent,
    prerendered_div,
)
from webcompy.elements import html
from webcompy.elements.types._repeat import RepeatElement
from webcompy.elements.types._suspense import SuspenseElement
from webcompy.elements.types._switch import SwitchElement
from webcompy.elements.types._transition import TransitionElement
from webcompy.signal import ReactiveList, Signal

pytestmark = pytest.mark.usefixtures("fake_browser_full")


@pytest.mark.asyncio
async def test_suspense_resolved_repeat_is_wired_after_hydration(eager_scheduler):
    rl = ReactiveList(["a", "b"])
    rep = RepeatElement(rl, lambda item: html.DIV({}, item))

    content_ssr = prerendered_div()
    it_a = prerendered_div("a")
    it_b = prerendered_div("b")
    content_ssr.appendChild(it_a)
    content_ssr.appendChild(it_b)
    parent = make_prerendered_parent(content_ssr)

    suspense = SuspenseElement(
        fallback=lambda: html.P({}, "loading"),
        children=lambda: html.DIV({}, rep),
    )
    suspense._parent = parent
    suspense._node_idx = 0
    parent._children = [suspense]

    suspense._hydrate_node()
    assert content_ssr.parentNode is parent._node_cache

    await suspense._render()
    await eager_scheduler.await_pending()

    assert parent._node_cache.childNodes[0] is content_ssr
    assert parent._node_cache.childNodes[0].childNodes.length == 2
    assert rep._signal_activated is True

    rl.append("c")
    await asyncio.sleep(0)
    assert parent._node_cache.childNodes[0].childNodes.length == 3


@pytest.mark.asyncio
async def test_transition_repeat_is_wired_after_hydration(eager_scheduler):
    from webcompy.signal import Signal

    rl = ReactiveList(["a", "b"])
    rep = RepeatElement(rl, lambda item: html.DIV({}, item))
    show = Signal(True)

    content_ssr = prerendered_div()
    it_a = prerendered_div("a")
    it_b = prerendered_div("b")
    content_ssr.appendChild(it_a)
    content_ssr.appendChild(it_b)
    parent = make_prerendered_parent(content_ssr)

    transition = TransitionElement(
        {"name": "fade", "duration": 100},
        lambda: html.DIV({}, rep) if show.value else None,
    )
    transition._parent = parent
    transition._node_idx = 0
    parent._children = [transition]

    transition._hydrate_node()
    assert content_ssr.parentNode is parent._node_cache

    await transition._render()
    await eager_scheduler.await_pending()

    assert parent._node_cache.childNodes[0] is content_ssr
    assert parent._node_cache.childNodes[0].childNodes.length == 2
    assert rep._signal_activated is True


@pytest.mark.asyncio
async def test_repeat_first_refresh_preserves_adopted_ssr_children(eager_scheduler):
    from tests.test_hydration_preservation_helpers import make_prerendered_parent

    rl = ReactiveList(["a", "b"])
    rep = RepeatElement(rl, lambda item: html.DIV({}, item))
    it_a = prerendered_div("a")
    it_b = prerendered_div("b")
    parent = make_prerendered_parent(it_a, it_b)
    rep._parent = parent
    rep._node_idx = 0
    parent._children = [rep]

    rep._hydrate_node()
    await rep._render()
    await eager_scheduler.await_pending()

    assert parent._node_cache.childNodes[0] is it_a
    assert parent._node_cache.childNodes[1] is it_b
    assert rep._signal_activated is True

    rl.append("c")
    await asyncio.sleep(0)
    assert parent._node_cache.childNodes.length == 3
    assert parent._node_cache.childNodes[2].textContent == "c"


@pytest.mark.asyncio
async def test_repeat_len_mismatch_preserves_adopted_nodes(eager_scheduler):
    from tests.test_hydration_preservation_helpers import make_prerendered_parent
    from webcompy.signal import ReactiveList

    rl = ReactiveList(["a", "b", "c"])
    rep = RepeatElement(rl, lambda item: html.DIV({}, item))
    it_a = prerendered_div("a")
    it_b = prerendered_div("b")
    parent = make_prerendered_parent(it_a, it_b)
    rep._parent = parent
    rep._node_idx = 0
    parent._children = [rep]

    rep._hydrate_node()
    assert rep._adoption_preserved is True

    await rep._render()
    await eager_scheduler.await_pending()
    assert parent._node_cache.childNodes.length == 3
    assert parent._node_cache.childNodes[0] is it_a
    assert parent._node_cache.childNodes[1] is it_b
    assert parent._node_cache.childNodes[2].textContent == "c"


@pytest.mark.asyncio
async def test_repeat_partial_adoption_preserves_matched_nodes(eager_scheduler):
    from tests.test_hydration_preservation_helpers import make_prerendered_parent
    from webcompy_testing import FakeDOMNode

    rl = ReactiveList(["a", "b"])
    rep = RepeatElement(rl, lambda item: html.DIV({}, item))
    it_a = prerendered_div("a")
    wrong = FakeDOMNode("span")
    wrong.__webcompy_prerendered_node__ = True
    parent = make_prerendered_parent(it_a, wrong)
    rep._parent = parent
    rep._node_idx = 0
    parent._children = [rep]

    rep._hydrate_node()
    assert rep._adoption_preserved is True

    await rep._render()
    await eager_scheduler.await_pending()
    assert parent._node_cache.childNodes.length == 2
    assert parent._node_cache.childNodes[0] is it_a
    assert parent._node_cache.childNodes[1].textContent == "b"


@pytest.mark.asyncio
async def test_switch_first_refresh_preserves_adopted_ssr_branch(eager_scheduler):
    enabled = Signal(True)
    branch = html.DIV({"class": "on"}, "on-content")
    on_ssr = prerendered_div("on-content")
    on_ssr.setAttribute("class", "on")
    parent = make_prerendered_parent(on_ssr)

    sw = SwitchElement([(enabled, lambda: branch)], lambda: None)
    sw._parent = parent
    sw._node_idx = 0
    parent._children = [sw]

    sw._hydrate_node()
    assert sw._rendered_idx == 0
    assert sw._children[0]._node_cache is on_ssr

    await sw._render()
    await eager_scheduler.await_pending()

    assert parent._node_cache.childNodes[0] is on_ssr
    assert parent._node_cache.childNodes[0].getAttribute("class") == "on"


@pytest.mark.asyncio
async def test_switch_condition_change_after_hydration_patches(eager_scheduler):
    enabled = Signal(True)
    on_branch = html.DIV({"class": "on"}, "on-content")
    off_ssr = prerendered_div("off-content")
    off_ssr.setAttribute("class", "off")
    parent = make_prerendered_parent(off_ssr)

    sw = SwitchElement(
        [(enabled, lambda: on_branch)],
        lambda: html.DIV({"class": "off"}, "off-content"),
    )
    sw._parent = parent
    sw._node_idx = 0
    parent._children = [sw]

    # Prerendered SSR branch is "off" (default active), but restored state is enabled:
    # hydration adopts the node and the recovered content matches the enabled branch.
    sw._hydrate_node()
    await sw._render()
    await eager_scheduler.await_pending()

    assert parent._node_cache.childNodes[0].getAttribute("class") == "on"
    assert parent._node_cache.childNodes[0].textContent == "on-content"


@pytest.mark.asyncio
async def test_switch_toggle_after_hydration_patches_branch(eager_scheduler):
    enabled = Signal(True)
    on_branch = html.DIV({"class": "on"}, "on-content")
    off_branch = html.DIV({"class": "off"}, "off-content")
    on_ssr = prerendered_div("on-content")
    on_ssr.setAttribute("class", "on")
    parent = make_prerendered_parent(on_ssr)

    sw = SwitchElement(
        [(enabled, lambda: on_branch)],
        lambda: off_branch,
    )
    sw._parent = parent
    sw._node_idx = 0
    parent._children = [sw]

    sw._hydrate_node()
    await sw._render()
    await eager_scheduler.await_pending()
    assert parent._node_cache.childNodes[0] is on_ssr

    enabled.value = False
    await asyncio.sleep(0)
    assert parent._node_cache.childNodes[0].getAttribute("class") == "off"


@pytest.mark.asyncio
async def test_switch_adopted_branch_nested_repeat_stays_wired(eager_scheduler):
    rl = ReactiveList(["a", "b"])
    rep = RepeatElement(rl, lambda item: html.DIV({}, item))
    enabled = Signal(True)

    content_ssr = prerendered_div()
    it_a = prerendered_div("a")
    it_b = prerendered_div("b")
    content_ssr.appendChild(it_a)
    content_ssr.appendChild(it_b)
    parent = make_prerendered_parent(content_ssr)

    sw = SwitchElement([(enabled, lambda: html.DIV({}, rep))], lambda: None)
    sw._parent = parent
    sw._node_idx = 0
    parent._children = [sw]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sw._hydrate_node()
        await sw._render()
        await eager_scheduler.await_pending()

    never_awaited = [w for w in caught if "was never awaited" in str(w.message)]
    assert never_awaited == [], f"hydration-render wrapper coroutine dropped: {never_awaited!r}"

    assert parent._node_cache.childNodes[0] is content_ssr
    assert rep._signal_activated is True

    rl.append("c")
    await asyncio.sleep(0)
    assert parent._node_cache.childNodes[0].childNodes.length == 3


@pytest.mark.asyncio
async def test_keyed_repeat_reconciles_after_hydration(eager_scheduler):
    from tests.test_hydration_preservation_helpers import make_prerendered_parent

    rl = ReactiveList(["a", "b"])
    rep = RepeatElement(
        rl,
        lambda item, key: html.DIV({"data-key": key}, item),
        key=lambda item: item,
    )
    it_a = prerendered_div("a")
    it_a.setAttribute("data-key", "a")
    it_b = prerendered_div("b")
    it_b.setAttribute("data-key", "b")
    parent = make_prerendered_parent(it_a, it_b)
    rep._parent = parent
    rep._node_idx = 0
    parent._children = [rep]

    rep._hydrate_node()
    await rep._render()
    await eager_scheduler.await_pending()

    assert parent._node_cache.childNodes[0] is it_a
    assert parent._node_cache.childNodes[1] is it_b
    assert rep._signal_activated is True

    rl.pop(0)
    await asyncio.sleep(0)
    assert parent._node_cache.childNodes.length == 1
    assert parent._node_cache.childNodes[0] is it_b


@pytest.mark.asyncio
async def test_hydration_fallback_creates_single_node(eager_scheduler):
    from webcompy_testing import FakeDOMNode

    rl = ReactiveList(["a", "b", "c"])
    rep = RepeatElement(rl, lambda item: html.DIV({}, item))
    it_a = prerendered_div("a")
    it_b = prerendered_div("b")
    parent = make_prerendered_parent(it_a, it_b)
    rep._parent = parent
    rep._node_idx = 0
    parent._children = [rep]

    created: list[str] = []
    original_init = FakeDOMNode.__init__

    def counted_init(self, name, **kwargs):
        created.append(name)
        original_init(self, name, **kwargs)

    FakeDOMNode.__init__ = counted_init
    try:
        rep._hydrate_node()
    finally:
        FakeDOMNode.__init__ = original_init

    c_child = rep._children[2]
    assert c_child._node_cache is not None
    assert c_child._node_cache.parentNode is None
    assert created.count("div") == 1, f"fallback created multiple div nodes: {created!r}"
    assert created.count("#text") == 1, f"fallback created multiple text nodes: {created!r}"

    await rep._render()
    await eager_scheduler.await_pending()
    assert c_child._node_cache.parentNode is parent._node_cache


def test_fallback_element_reuses_created_node():
    from webcompy_testing import FakeDOMNode

    parent = make_prerendered_parent()
    el = html.DIV({"data-x": "1"}, "content")
    el._parent = parent
    el._node_idx = 0
    parent._children = [el]

    created: list[FakeDOMNode] = []
    original_create = el._create_node

    def counted_create():
        node = original_create()
        created.append(node)
        return node

    el._create_node = counted_create
    el._hydrate_node()

    assert len(created) == 1, f"fallback created {len(created)} div nodes instead of one"
    assert el._node_cache is created[0], "fallback must reuse the created node as _node_cache"
    assert el._node_cache.nodeName.lower() == "div"
