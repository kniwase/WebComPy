"""Unit tests for ui form controls (browserless via TestRenderer)."""

from __future__ import annotations

from typing import Any

import pytest

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.exception import WebComPyException
from webcompy.forms import use_field
from webcompy.signal import Signal
from webcompy.ui.headless import Input
from webcompy.ui.headless._form_field_context import FORM_FIELD_CONTEXT_KEY, FormFieldContext
from webcompy_testing import TestRenderer


def _find_tag(node: Any, tag: str) -> Any:
    """Return the first virtual descendant with the given tag name."""
    stack = [node]
    while stack:
        current = stack.pop()
        if getattr(current, "nodeName", "").upper() == tag:
            return current
        children = getattr(current, "childNodes", None)
        if children:
            for i in range(children.length - 1, -1, -1):
                stack.append(children[i])
    return None


def _required_field(initial: str = "") -> Any:
    return use_field(Signal(initial), validators=[lambda v: "required" if not v else None])


class TestFormFieldContextInjection:
    """Task 2.5: controls consume a FormFieldContext provided by an ancestor."""

    def test_control_adopts_provided_ids(self) -> None:
        field = _required_field()

        @define_component(custom_element_name="test-ff-provider")
        def Provider(ctx: ComponentContext) -> Any:
            ctx.provide(
                FORM_FIELD_CONTEXT_KEY,
                FormFieldContext(control_id="ctrl-1", error_id="err-1", label="Name"),
            )
            return html.DIV({}, Input({"field": field}))

        with TestRenderer.render(Provider) as result:
            input_node = _find_tag(result.body_node, "INPUT")
            assert input_node is not None
            assert input_node.getAttribute("id") == "ctrl-1"
            assert input_node.getAttribute("aria-describedby") is None

    def test_describedby_appears_only_when_gated_invalid(self) -> None:
        field = _required_field()

        @define_component(custom_element_name="test-ff-provider-gated")
        def Provider(ctx: ComponentContext) -> Any:
            ctx.provide(
                FORM_FIELD_CONTEXT_KEY,
                FormFieldContext(control_id="ctrl-2", error_id="err-2", label="Name"),
            )
            return html.DIV({}, Input({"field": field}))

        with TestRenderer.render(Provider) as result:
            input_node = _find_tag(result.body_node, "INPUT")
            assert input_node.getAttribute("data-state") == "valid"
            field.touched.value = True
            assert input_node.getAttribute("data-state") == "invalid"
            assert input_node.getAttribute("aria-invalid") == "true"
            assert input_node.getAttribute("aria-describedby") == "err-2"
            field.value.value = "filled"
            assert input_node.getAttribute("data-state") == "valid"
            assert input_node.getAttribute("aria-describedby") is None
            assert input_node.getAttribute("aria-invalid") is None

    def test_control_works_without_context(self) -> None:
        field = _required_field()

        @define_component(custom_element_name="test-ff-standalone")
        def Page(ctx: ComponentContext) -> Any:
            return Input({"field": field, "id": "manual-id"})

        with TestRenderer.render(Page) as result:
            input_node = _find_tag(result.body_node, "INPUT")
            assert input_node.getAttribute("id") == "manual-id"
            field.touched.value = True
            assert input_node.getAttribute("aria-describedby") is None


class TestInputBinding:
    """Binding contract for the headless Input."""

    def test_both_modes_rejected(self) -> None:
        field = _required_field()

        @define_component(custom_element_name="test-input-both")
        def Page(ctx: ComponentContext) -> Any:
            return Input({"field": field, "value": "x"})

        with pytest.raises(WebComPyException, match="not both"), TestRenderer.render(Page):
            pass

    def test_raw_value_mode(self) -> None:
        changes: list[str] = []

        @define_component(custom_element_name="test-input-raw")
        def Page(ctx: ComponentContext) -> Any:
            return Input({"value": "seed", "on_change": changes.append})

        with TestRenderer.render(Page) as result:
            input_node = _find_tag(result.body_node, "INPUT")
            assert input_node.getAttribute("value") == "seed"
            assert input_node.getAttribute("data-state") == "valid"

    def test_unsupported_input_type_rejected(self) -> None:
        @define_component(custom_element_name="test-input-type")
        def Page(ctx: ComponentContext) -> Any:
            return Input({"value": "x", "input_type": "color"})

        with pytest.raises(WebComPyException, match="input_type"), TestRenderer.render(Page):
            pass
