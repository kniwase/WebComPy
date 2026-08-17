from __future__ import annotations

import asyncio

import pytest

from tests.test_hydration_preservation_helpers import (
    FakeRootElement,
    make_prerendered_parent,
)
from webcompy.components._component import _active_app_context
from webcompy.elements.types._text import RawHTMLElement
from webcompy.hydration._report import HydrationReporter
from webcompy.signal import Signal
from webcompy_testing import FakeDOMNode

pytestmark = pytest.mark.usefixtures("fake_browser_full")


class _FakeCtx:
    def __init__(self) -> None:
        self._hydration_in_progress: bool = True
        self._hydration_reporter = HydrationReporter()


@pytest.fixture
def hydration_window():
    ctx = _FakeCtx()
    token = _active_app_context.set(ctx)
    yield ctx
    _active_app_context.reset(token)


def _prerendered_wrapper(inner_html: str) -> tuple[FakeDOMNode, FakeDOMNode]:
    wrapper = FakeDOMNode("span")
    wrapper.__webcompy_prerendered_node__ = True
    child = FakeDOMNode("span")
    child.__webcompy_prerendered_node__ = True
    wrapper.appendChild(child)
    wrapper.innerHTML = inner_html
    return wrapper, child


def _make_raw(html: str | Signal, parent: FakeRootElement) -> RawHTMLElement:
    raw = RawHTMLElement(html)
    raw._parent = parent
    raw._node_idx = 0
    parent._children = [raw]
    return raw


def test_raw_html_adoption_preserves_children_when_content_matches(hydration_window):
    value = "<span class='tok-kw'>def</span>"
    wrapper, child = _prerendered_wrapper(value)
    parent = make_prerendered_parent(wrapper)
    raw = _make_raw(value, parent)

    raw._hydrate_node()

    assert raw._node_cache is wrapper
    assert child.parentNode is wrapper
    assert wrapper.innerHTML == value
    assert len(hydration_window._hydration_reporter.records) == 0


def test_raw_html_adoption_patches_and_records_when_content_differs(hydration_window):
    value = "<span class='tok-kw'>def</span>"
    wrapper, _ = _prerendered_wrapper("<span>old</span>")
    parent = make_prerendered_parent(wrapper)
    raw = _make_raw(value, parent)

    raw._hydrate_node()

    assert raw._node_cache is wrapper
    assert wrapper.innerHTML == value
    records = hydration_window._hydration_reporter.records
    assert len(records) == 1
    record = records[0]
    assert record.kind == "raw_html"
    assert record.expected == value
    assert record.actual == "<span>old</span>"


def test_raw_html_adoption_skips_write_when_both_empty(hydration_window):
    wrapper = FakeDOMNode("span")
    wrapper.__webcompy_prerendered_node__ = True
    wrapper.innerHTML = ""
    parent = make_prerendered_parent(wrapper)
    raw = _make_raw("", parent)

    raw._hydrate_node()

    assert raw._node_cache is wrapper
    assert wrapper.innerHTML == ""
    assert len(hydration_window._hydration_reporter.records) == 0


@pytest.mark.asyncio
async def test_raw_html_signal_update_still_applies_after_adoption(hydration_window):
    signal = Signal("<span>one</span>")
    value = signal.value
    wrapper, _ = _prerendered_wrapper(value)
    parent = make_prerendered_parent(wrapper)
    raw = _make_raw(signal, parent)

    raw._hydrate_node()
    assert wrapper.innerHTML == value

    signal.value = "<span class='tok-num'>2</span>"
    await asyncio.sleep(0)
    assert wrapper.innerHTML == "<span class='tok-num'>2</span>"
