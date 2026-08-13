from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import FakeDOMNode
from webcompy.components import define_component, on_before_destroy
from webcompy.elements import Transition, html
from webcompy.elements.types._element import Element
from webcompy.elements.types._transition import TransitionElement
from webcompy.exception import WebComPyException
from webcompy.signal import Signal
from webcompy_testing import TestRenderer, create_test_app, render_app_html


class _FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _box_classes(result, testid: str) -> list[str]:
    node = result.find_by_attribute("data-testid", testid)
    if node is None:
        return []
    return (node.getAttribute("class") or "").split()


def _toggle_root(show: Signal[bool], name: str = "fade", duration: int | None = 100):
    @define_component
    def Root(context):
        return html.DIV(
            {},
            html.SPAN({"data-testid": "before"}, "before"),
            Transition(
                {"name": name, "duration": duration},
                lambda: html.DIV({"data-testid": "box"}, "box") if show.value else None,
            ),
            html.SPAN({"data-testid": "after"}, "after"),
        )

    return Root


class TestEnterSequence:
    def test_enter_class_order_and_node_retention(self) -> None:
        show = Signal(False)
        with TestRenderer.render(_toggle_root(show)) as result:
            assert result.find_by_attribute("data-testid", "box") is None

            show.value = True
            box = result.find_by_attribute("data-testid", "box")
            assert box is not None
            assert _box_classes(result, "box") == ["fade-enter-from"]

            result.transition_port.flush_frame()
            classes = _box_classes(result, "box")
            assert "fade-enter-from" not in classes
            assert "fade-enter-active" in classes
            assert "fade-enter-to" in classes
            assert result.find_by_attribute("data-testid", "box") is box

            result.transition_port.advance_time(100)
            assert _box_classes(result, "box") == []
            assert result.find_by_attribute("data-testid", "box") is box

    def test_initial_render_does_not_enter(self) -> None:
        show = Signal(True)
        with TestRenderer.render(_toggle_root(show)) as result:
            box = result.find_by_attribute("data-testid", "box")
            assert box is not None
            assert _box_classes(result, "box") == []
            result.transition_port.flush_frame()
            result.transition_port.advance_time(1000)
            assert _box_classes(result, "box") == []

    def test_same_tag_update_patches_without_classes(self) -> None:
        show = Signal(True)
        text = Signal("a")

        @define_component
        def Root(context):
            return html.DIV(
                {},
                Transition(
                    {"name": "fade", "duration": 100},
                    lambda: html.DIV({"data-testid": "box"}, text.value) if show.value else None,
                ),
            )

        with TestRenderer.render(Root) as result:
            box = result.find_by_attribute("data-testid", "box")
            assert box is not None
            text.value = "b"
            result.transition_port.flush_frame()
            result.transition_port.advance_time(1000)
            assert _box_classes(result, "box") == []
            assert result.find_by_attribute("data-testid", "box") is box
            assert box.textContent == "b"


class TestLeaveSequence:
    def _destroy_root(self, show: Signal[bool], destroyed: list[int]):
        @define_component
        def Root(context):
            @on_before_destroy
            def _cleanup():
                destroyed.append(1)

            return html.DIV(
                {},
                html.SPAN({"data-testid": "before"}, "before"),
                Transition(
                    {"name": "fade", "duration": 100},
                    lambda: html.DIV({"data-testid": "box"}, "box") if show.value else None,
                ),
                html.SPAN({"data-testid": "after"}, "after"),
            )

        return Root

    def test_leave_retains_node_then_removes(self) -> None:
        show = Signal(True)
        with TestRenderer.render(_toggle_root(show)) as result:
            assert result.find_by_attribute("data-testid", "box") is not None

            show.value = False
            assert _box_classes(result, "box") == ["fade-leave-from"]
            assert result.find_by_attribute("data-testid", "box") is not None

            result.transition_port.flush_frame()
            classes = _box_classes(result, "box")
            assert "fade-leave-from" not in classes
            assert "fade-leave-active" in classes
            assert "fade-leave-to" in classes
            assert result.find_by_attribute("data-testid", "box") is not None

            result.transition_port.advance_time(100)
            assert result.find_by_attribute("data-testid", "box") is None

    def test_leave_destroys_child_consumers_and_no_orphans(self) -> None:
        show = Signal(True)
        counter = Signal(0)
        destroyed: list[int] = []

        @define_component
        def Child(context):
            @on_before_destroy
            def _cleanup():
                destroyed.append(1)

            return html.SPAN({"data-testid": "box", "data-x": counter}, "box")

        @define_component
        def Root(context):
            return html.DIV(
                {},
                Transition(
                    {"name": "fade", "duration": 100},
                    lambda: Child(None) if show.value else None,
                ),
            )

        with TestRenderer.render(Root) as result:
            assert counter.consumers is not None
            show.value = False
            result.transition_port.flush_frame()
            result.transition_port.advance_time(100)
            assert result.find_by_attribute("data-testid", "box") is None
            assert counter.consumers is None
            assert destroyed == [1]
            root_node = result._root_node
            assert root_node.childNodes.length == 0


class TestDurationResolution:
    def test_explicit_duration_wins_over_styles(self) -> None:
        show = Signal(False)
        with TestRenderer.render(_toggle_root(show, duration=50)) as result:
            show.value = True
            result.transition_port.flush_frame()
            box = result.find_by_attribute("data-testid", "box")
            result.transition_port.set_style(box, "transition-duration", "10000ms")
            result.transition_port.advance_time(50)
            assert _box_classes(result, "box") == []

    def test_computed_style_duration_used_when_no_prop(self) -> None:
        show = Signal(False)
        with TestRenderer.render(_toggle_root(show, duration=None)) as result:
            show.value = True
            box = result.find_by_attribute("data-testid", "box")
            result.transition_port.set_style(box, "transition-duration", "150ms")
            result.transition_port.flush_frame()
            assert "fade-enter-active" in _box_classes(result, "box")
            result.transition_port.advance_time(150)
            assert _box_classes(result, "box") == []

    def test_animation_duration_plus_delay_used(self) -> None:
        show = Signal(False)
        with TestRenderer.render(_toggle_root(show, duration=None)) as result:
            show.value = True
            box = result.find_by_attribute("data-testid", "box")
            result.transition_port.set_style(box, "animation-duration", "1s")
            result.transition_port.set_style(box, "animation-delay", "250ms")
            result.transition_port.flush_frame()
            result.transition_port.advance_time(1249)
            assert "fade-enter-active" in _box_classes(result, "box")
            result.transition_port.advance_time(1)
            assert _box_classes(result, "box") == []

    def test_multi_property_duration_repeats_last_delay(self) -> None:
        show = Signal(False)
        with TestRenderer.render(_toggle_root(show, duration=None)) as result:
            show.value = True
            box = result.find_by_attribute("data-testid", "box")
            result.transition_port.set_style(box, "transition-duration", "1s, 2s")
            result.transition_port.set_style(box, "transition-delay", "500ms")
            result.transition_port.flush_frame()
            result.transition_port.advance_time(2499)
            assert "fade-enter-active" in _box_classes(result, "box")
            result.transition_port.advance_time(1)
            assert _box_classes(result, "box") == []

    def test_animation_multi_property_duration_repeats_last_delay(self) -> None:
        show = Signal(False)
        with TestRenderer.render(_toggle_root(show, duration=None)) as result:
            show.value = True
            box = result.find_by_attribute("data-testid", "box")
            result.transition_port.set_style(box, "animation-duration", "1s, 2s")
            result.transition_port.set_style(box, "animation-delay", "500ms")
            result.transition_port.flush_frame()
            result.transition_port.advance_time(2499)
            assert "fade-enter-active" in _box_classes(result, "box")
            result.transition_port.advance_time(1)
            assert _box_classes(result, "box") == []

    def test_no_duration_finalizes_immediately_with_warning(self, monkeypatch) -> None:
        import webcompy.logging

        warnings: list[tuple[Any, ...]] = []
        monkeypatch.setattr(
            webcompy.logging,
            "warning",
            lambda *values: warnings.append(values),
        )
        show = Signal(False)
        with TestRenderer.render(_toggle_root(show, duration=None)) as result:
            show.value = True
            result.transition_port.flush_frame()
            assert _box_classes(result, "box") == []
            assert len(warnings) == 1
            assert "no transition or animation duration" in str(warnings[0])

    def test_explicit_zero_finalizes_without_warning(self, monkeypatch) -> None:
        import webcompy.logging

        warnings: list[tuple[Any, ...]] = []
        monkeypatch.setattr(
            webcompy.logging,
            "warning",
            lambda *values: warnings.append(values),
        )
        show = Signal(False)
        with TestRenderer.render(_toggle_root(show, duration=0)) as result:
            show.value = True
            result.transition_port.flush_frame()
            assert _box_classes(result, "box") == []
            assert warnings == []

    def test_timeout_finalizes_when_end_events_never_fire(self) -> None:
        show = Signal(False)
        with TestRenderer.render(_toggle_root(show)) as result:
            show.value = True
            result.transition_port.flush_frame()
            assert "fade-enter-active" in _box_classes(result, "box")
            result.transition_port.advance_time(100)
            assert _box_classes(result, "box") == []

    def test_end_event_on_node_finalizes_early(self) -> None:
        from webcompy_server.ports import VirtualDOMEvent

        show = Signal(False)
        with TestRenderer.render(_toggle_root(show)) as result:
            show.value = True
            result.transition_port.flush_frame()
            assert "fade-enter-active" in _box_classes(result, "box")
            box = result.find_by_attribute("data-testid", "box")
            assert box is not None
            box.dispatchEvent(VirtualDOMEvent("transitionend", bubbles=True))
            assert _box_classes(result, "box") == []

    def test_end_event_from_descendant_does_not_finalize(self) -> None:
        from webcompy_server.ports import VirtualDOMEvent

        show = Signal(True)

        @define_component
        def Root(context):
            return html.DIV(
                {},
                Transition(
                    {"name": "fade", "duration": 100},
                    lambda: (
                        html.DIV(
                            {"data-testid": "box"},
                            html.SPAN({"data-testid": "inner"}, "inner"),
                        )
                        if show.value
                        else None
                    ),
                ),
            )

        with TestRenderer.render(Root) as result:
            show.value = False
            result.transition_port.flush_frame()
            inner = result.find_by_attribute("data-testid", "inner")
            box = result.find_by_attribute("data-testid", "box")
            assert inner is not None and box is not None
            inner.dispatchEvent(VirtualDOMEvent("transitionend", bubbles=True))
            assert "fade-leave-active" in _box_classes(result, "box")
            result.transition_port.advance_time(100)
            assert result.find_by_attribute("data-testid", "box") is None


class TestNodeAccounting:
    def test_sibling_positions_stable_during_leave_and_reindex_once(self, monkeypatch) -> None:
        show = Signal(True)
        with TestRenderer.render(_toggle_root(show)) as result:
            before, transition, after = result._instance._children

            reindex_calls: list[int] = []
            root = transition._parent
            original_reindex = root._re_index_children

            def counting_reindex(recursive: bool = False) -> None:
                reindex_calls.append(1)
                original_reindex(recursive)

            monkeypatch.setattr(root, "_re_index_children", counting_reindex)
            reindex_calls.clear()

            assert before._node_idx == 0
            assert transition._node_idx == 1
            assert after._node_idx == 2

            show.value = False
            assert after._node_idx == 2
            assert reindex_calls == []

            result.transition_port.flush_frame()
            assert after._node_idx == 2
            assert reindex_calls == []

            result.transition_port.advance_time(100)
            assert reindex_calls == [1]
            assert transition._node_count == 0
            assert after._node_idx == 1
            texts = [node.textContent for node in root._get_node().childNodes]
            assert texts == ["before", "after"]

    def test_leave_completion_reindexes_without_refresh_reevaluation(self, monkeypatch) -> None:
        show = Signal(True)
        with TestRenderer.render(_toggle_root(show)) as result:
            transition = result._instance._children[1]
            refresh_calls: list[Any] = []
            original_refresh = TransitionElement._refresh

            def counting_refresh(self, *args: Any):
                refresh_calls.append(args)
                return original_refresh(self, *args)

            monkeypatch.setattr(TransitionElement, "_refresh", counting_refresh)

            show.value = False
            result.transition_port.flush_frame()
            refresh_calls.clear()

            result.transition_port.advance_time(100)
            assert refresh_calls == []
            assert transition._node_count == 0
            assert result.find_by_attribute("data-testid", "box") is None


class TestReplacementAndInterruption:
    def _replacement_root(self, a_show: Signal[bool], b_show: Signal[bool]):
        @define_component
        def Root(context):
            return html.DIV(
                {},
                Transition(
                    {"name": "fade", "duration": 100},
                    lambda: (
                        html.DIV({"data-testid": "a"}, "a")
                        if a_show.value
                        else (html.SPAN({"data-testid": "b"}, "b") if b_show.value else None)
                    ),
                ),
            )

        return Root

    def test_replacement_leaves_then_enters(self) -> None:
        a_show, b_show = Signal(True), Signal(False)
        with TestRenderer.render(self._replacement_root(a_show, b_show)) as result:
            assert result.find_by_attribute("data-testid", "a") is not None

            b_show.value = True
            a_show.value = False
            assert result.find_by_attribute("data-testid", "b") is None
            assert "fade-leave-from" in _box_classes(result, "a")

            result.transition_port.flush_frame()
            assert result.find_by_attribute("data-testid", "a") is not None
            assert result.find_by_attribute("data-testid", "b") is None

            result.transition_port.advance_time(100)
            assert result.find_by_attribute("data-testid", "a") is None
            assert result.find_by_attribute("data-testid", "b") is not None
            assert "fade-enter-from" in _box_classes(result, "b")

            result.transition_port.flush_frame()
            assert "fade-enter-active" in _box_classes(result, "b")
            result.transition_port.advance_time(100)
            assert _box_classes(result, "b") == []

    def test_new_child_during_leave_finalizes_leaving_node_first(self) -> None:
        a_show, b_show = Signal(True), Signal(False)
        with TestRenderer.render(self._replacement_root(a_show, b_show)) as result:
            a_show.value = False
            result.transition_port.flush_frame()
            assert "fade-leave-active" in _box_classes(result, "a")

            b_show.value = True
            assert result.find_by_attribute("data-testid", "a") is None
            assert result.find_by_attribute("data-testid", "b") is not None
            assert "fade-enter-from" in _box_classes(result, "b")
            assert _box_classes(result, "a") == []

    def test_replacement_reindexes_once(self, monkeypatch) -> None:
        a_show, b_show = Signal(True), Signal(False)
        with TestRenderer.render(self._replacement_root(a_show, b_show)) as result:
            transition = result._instance._children[0]
            root = transition._parent
            original_reindex = root._re_index_children
            reindex_calls: list[int] = []

            def counting_reindex(recursive: bool = False) -> None:
                reindex_calls.append(1)
                original_reindex(recursive)

            monkeypatch.setattr(root, "_re_index_children", counting_reindex)
            reindex_calls.clear()

            a_show.value = False
            result.transition_port.flush_frame()
            assert reindex_calls == []

            b_show.value = True
            assert result.find_by_attribute("data-testid", "a") is None
            assert result.find_by_attribute("data-testid", "b") is not None
            assert "fade-enter-from" in _box_classes(result, "b")
            assert reindex_calls == [1]

    def test_new_child_during_enter_leaves_then_enters(self) -> None:
        a_show, b_show = Signal(False), Signal(False)
        with TestRenderer.render(self._replacement_root(a_show, b_show)) as result:
            a_show.value = True
            assert "fade-enter-from" in _box_classes(result, "a")

            b_show.value = True
            a_show.value = False
            assert "fade-leave-from" in _box_classes(result, "a")
            assert result.find_by_attribute("data-testid", "b") is None

            result.transition_port.flush_frame()
            assert "fade-leave-active" in _box_classes(result, "a")
            assert result.find_by_attribute("data-testid", "b") is None

            result.transition_port.advance_time(100)
            assert result.find_by_attribute("data-testid", "a") is None
            assert "fade-enter-from" in _box_classes(result, "b")

            result.transition_port.flush_frame()
            assert "fade-enter-active" in _box_classes(result, "b")
            result.transition_port.advance_time(100)
            assert _box_classes(result, "b") == []

    def test_none_during_enter_applies_leave_then_removes(self) -> None:
        show = Signal(False)
        with TestRenderer.render(_toggle_root(show)) as result:
            show.value = True
            assert "fade-enter-from" in _box_classes(result, "box")

            show.value = False
            assert "fade-leave-from" in _box_classes(result, "box")

            result.transition_port.flush_frame()
            assert "fade-leave-active" in _box_classes(result, "box")
            result.transition_port.advance_time(100)
            assert result.find_by_attribute("data-testid", "box") is None

    def test_leave_while_leaving_is_noop(self) -> None:
        show = Signal(True)
        with TestRenderer.render(_toggle_root(show)) as result:
            show.value = False
            result.transition_port.flush_frame()
            show.value = False
            assert "fade-leave-active" in _box_classes(result, "box")
            result.transition_port.advance_time(100)
            assert result.find_by_attribute("data-testid", "box") is None

    def _two_signal_root(self, show: Signal[bool], extra: Signal[bool]):
        @define_component
        def Root(context):
            return html.DIV(
                {},
                Transition(
                    {"name": "fade", "duration": 100},
                    lambda: html.DIV({"data-testid": "box"}, "box") if show.value or extra.value else None,
                ),
            )

        return Root

    def test_same_tag_update_during_leave_completes_leave_then_enters(self) -> None:
        show, extra = Signal(True), Signal(False)
        with TestRenderer.render(self._two_signal_root(show, extra)) as result:
            show.value = False
            result.transition_port.flush_frame()
            assert "fade-leave-active" in _box_classes(result, "box")

            extra.value = True
            assert result.find_by_attribute("data-testid", "box") is not None
            assert "fade-leave-active" in _box_classes(result, "box")

            result.transition_port.advance_time(100)
            assert result.find_by_attribute("data-testid", "box") is not None
            assert "fade-enter-from" in _box_classes(result, "box")

            result.transition_port.flush_frame()
            assert "fade-enter-active" in _box_classes(result, "box")
            result.transition_port.advance_time(100)
            assert _box_classes(result, "box") == []

    def _switch_root(self, show: Signal[bool], wrap: Signal[bool]):
        from webcompy.elements import switch

        @define_component
        def Root(context):
            return html.DIV(
                {},
                switch(
                    {
                        "case": wrap,
                        "generator": lambda: html.DIV(
                            {"data-testid": "wrap"},
                            Transition(
                                {"name": "fade", "duration": 100},
                                lambda: html.DIV({"data-testid": "box"}, "b") if show.value else None,
                            ),
                        ),
                    },
                    default=None,
                ),
            )

        return Root

    def test_staged_pending_child_discarded_when_generator_returns_none(self) -> None:
        show, extra = Signal(True), Signal(False)
        with TestRenderer.render(self._two_signal_root(show, extra)) as result:
            transition = result._instance._children[0]
            show.value = False
            result.transition_port.flush_frame()
            extra.value = True
            assert transition._pending_child is not None
            extra.value = False
            assert transition._pending_child is None
            result.transition_port.advance_time(100)
            assert result.find_by_attribute("data-testid", "box") is None

    def test_revert_during_leave_completion_discards_staged_child(self, monkeypatch) -> None:
        show, extra = Signal(True), Signal(False)
        with TestRenderer.render(self._two_signal_root(show, extra)) as result:
            transition = result._instance._children[0]
            show.value = False
            result.transition_port.flush_frame()
            extra.value = True
            assert transition._pending_child is not None

            gated = True
            original_refresh = TransitionElement._refresh

            async def gated_refresh(self, *args: Any):
                if gated:
                    return
                return await original_refresh(self, *args)

            monkeypatch.setattr(TransitionElement, "_refresh", gated_refresh)
            extra.value = False
            gated = False
            result.transition_port.advance_time(100)
            assert result.find_by_attribute("data-testid", "box") is None
            assert transition._pending_child is None

    def test_discarding_staged_child_does_not_create_dom_node(self, monkeypatch) -> None:
        from webcompy_testing._dom import FakeDOMNode

        created: list[str] = []
        original_init = FakeDOMNode.__init__

        def counting_init(self, tag: str = "div", text_content: str | None = None):
            if not tag.startswith("#text"):
                created.append(tag)
            original_init(self, tag, text_content)

        monkeypatch.setattr(FakeDOMNode, "__init__", counting_init)

        show, extra = Signal(True), Signal(False)
        with TestRenderer.render(self._two_signal_root(show, extra)) as result:
            show.value = False
            result.transition_port.flush_frame()
            before = len(created)
            extra.value = True
            extra.value = False
            assert len(created) == before
            result.transition_port.advance_time(100)
            assert result.find_by_attribute("data-testid", "box") is None

    def test_removing_transition_itself_removes_child_immediately(self) -> None:
        show, wrap = Signal(True), Signal(True)
        with TestRenderer.render(self._switch_root(show, wrap)) as result:
            assert result.find_by_attribute("data-testid", "box") is not None
            wrap.value = False
            assert result.find_by_attribute("data-testid", "wrap") is None
            assert result.find_by_attribute("data-testid", "box") is None

    def test_removing_transition_during_leave_removes_child_immediately(self) -> None:
        show, wrap = Signal(True), Signal(True)
        with TestRenderer.render(self._switch_root(show, wrap)) as result:
            show.value = False
            result.transition_port.flush_frame()
            assert "fade-leave-active" in _box_classes(result, "box")
            wrap.value = False
            assert result.find_by_attribute("data-testid", "box") is None


class TestSsrAndHydration:
    def test_ssr_output_has_no_transition_classes(self) -> None:
        show = Signal(True)

        @define_component
        def SsrRoot(context):
            return html.DIV(
                {},
                Transition({"name": "fade"}, lambda: html.DIV({"class": "ssr-box"}, "x") if show.value else None),
            )

        app = create_test_app(root_component=SsrRoot)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "ssr-box" in html_str
        assert "fade-enter" not in html_str
        assert "fade-leave" not in html_str

    @pytest.mark.asyncio
    async def test_hydrated_content_does_not_enter(self, fake_browser_full) -> None:
        from webcompy.di._scope import _active_di_scope
        from webcompy.ports._keys import TRANSITION_PORT_KEY

        show = Signal(True)
        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        prerendered = FakeDOMNode("div")
        prerendered.__webcompy_prerendered_node__ = True
        parent._node_cache.appendChild(prerendered)

        transition = TransitionElement(
            {"name": "fade", "duration": 100},
            lambda: html.DIV({"class": "hydrated-box"}, "x") if show.value else None,
        )
        transition._parent = parent
        transition._node_idx = 0
        transition._hydrate_node()
        await transition._render()

        node = parent._node_cache.childNodes[0]
        classes = (node.getAttribute("class") or "").split()
        assert "fade-enter-from" not in classes
        assert "fade-enter-active" not in classes
        assert "fade-enter-to" not in classes
        port = _active_di_scope.get().inject(TRANSITION_PORT_KEY)
        port.flush_frame()
        port.advance_time(1000)
        classes = (node.getAttribute("class") or "").split()
        assert "fade-enter" not in classes
        assert "fade-leave" not in classes
        assert parent._node_cache.childNodes.length == 1


class TestValidation:
    def test_missing_name_raises(self) -> None:
        with pytest.raises(WebComPyException):
            TransitionElement({}, lambda: None)

    def test_empty_name_raises(self) -> None:
        with pytest.raises(WebComPyException):
            TransitionElement({"name": ""}, lambda: None)

    def test_negative_duration_raises(self) -> None:
        with pytest.raises(WebComPyException):
            TransitionElement({"name": "fade", "duration": -1}, lambda: None)

    def test_non_numeric_duration_raises(self) -> None:
        with pytest.raises(WebComPyException):
            TransitionElement({"name": "fade", "duration": "fast"}, lambda: None)

    def test_dynamic_child_shape_rejected(self) -> None:
        from webcompy.elements.types._fragment import FragmentElement

        show = Signal(True)

        @define_component
        def Root(context):
            return html.DIV(
                {},
                Transition(
                    {"name": "fade", "duration": 100},
                    lambda: FragmentElement([html.SPAN({}, "a"), html.SPAN({}, "b")]) if show.value else None,
                ),
            )

        with pytest.raises(WebComPyException):
            TestRenderer.render(Root)

    def test_text_child_shape_rejected(self) -> None:
        from webcompy.elements.types._text import TextElement

        show = Signal(True)

        @define_component
        def Root(context):
            return html.DIV(
                {},
                Transition(
                    {"name": "fade", "duration": 100},
                    lambda: TextElement("x") if show.value else None,
                ),
            )

        with pytest.raises(WebComPyException):
            TestRenderer.render(Root)


class TestReducedMotion:
    def test_reduced_motion_skips_sequences(self) -> None:
        show = Signal(False)
        with TestRenderer.render(_toggle_root(show)) as result:
            result.media_query_port.set_prefers_reduced_motion(True)

            show.value = True
            assert result.find_by_attribute("data-testid", "box") is not None
            assert _box_classes(result, "box") == []

            show.value = False
            assert result.find_by_attribute("data-testid", "box") is None

    def test_disabled_port_skips_sequences(self) -> None:
        show = Signal(False)
        with TestRenderer.render(_toggle_root(show)) as result:
            result.transition_port.set_enabled(False)

            show.value = True
            assert result.find_by_attribute("data-testid", "box") is not None
            assert _box_classes(result, "box") == []

            show.value = False
            assert result.find_by_attribute("data-testid", "box") is None
