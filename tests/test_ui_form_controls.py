"""Unit tests for ui form controls (browserless via TestRenderer)."""

from __future__ import annotations

from typing import Any

import pytest

from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.exception import WebComPyException
from webcompy.forms import use_field
from webcompy.signal import Signal
from webcompy.ui.headless import Checkbox, FormField, Input, RadioGroup, Select, Switch, Textarea
from webcompy.ui.headless._form_field_context import FORM_FIELD_CONTEXT_KEY, FormFieldContext
from webcompy_testing import TestRenderer


def _find_tag(node: Any, tag: str) -> Any:
    """Return the first virtual descendant with the given tag name."""
    for found in _find_all(node, lambda n: getattr(n, "nodeName", "").upper() == tag):
        return found
    return None


def _find_all(node: Any, predicate: Any) -> list[Any]:
    found = []
    stack = [node]
    while stack:
        current = stack.pop()
        if predicate(current):
            found.append(current)
        children = getattr(current, "childNodes", None)
        if children:
            for i in range(children.length - 1, -1, -1):
                stack.append(children[i])
    return found


def _set_app_ctx() -> tuple[Any, Any]:
    from webcompy.components import _component as _component_mod

    var = _component_mod._active_app_context
    return var, var.set(_DeterministicAppCtx())


def _required_field(initial: Any = "") -> Any:
    def check(v: Any) -> str | None:
        return "required" if not v else None

    return use_field(Signal(initial), validators=[check])


class _DeterministicAppCtx:
    """App context assigning ordinal-unique transfer ids (mirror of the overlay tests)."""

    def __init__(self) -> None:
        from webcompy.components._libs import generate_id

        self._generate_id = generate_id
        self._counters: dict[str, int] = {}
        self._defer_depth = 0
        self._deferred_callbacks: list[Any] = []
        self._hydration_payload_closed = False
        self._config = type("Config", (), {"on_error": staticmethod(lambda exc: None)})()

    def _next_transfer_id(self, name: str) -> str:
        ordinal = self._counters.get(name, 0)
        self._counters[name] = ordinal + 1
        return f"{self._generate_id(name)}#{ordinal}"


class TestFormFieldContextInjection:
    """6.4: controls consume a FormFieldContext provided by an ancestor."""

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


class TestBindingContract:
    """6.1: Field/raw binding modes and mutual exclusion."""

    def test_field_write_back_marks_dirty_and_blur_marks_touched(self) -> None:
        from webcompy_server.ports import VirtualDOMEvent

        field = use_field(Signal("hello"))

        @define_component(custom_element_name="test-bind-text")
        def Page(ctx: ComponentContext) -> Any:
            return Input({"field": field, "placeholder": "P"})

        with TestRenderer.render(Page) as result:
            input_node = _find_tag(result.body_node, "INPUT")
            input_node.value = "world"
            input_node.dispatchEvent(VirtualDOMEvent("input"))
            assert field.value.value == "world"
            assert field.dirty.value is True
            assert field.touched.value is False
            input_node.dispatchEvent(VirtualDOMEvent("blur"))
            assert field.touched.value is True

    def test_raw_value_mode_invokes_change_after_write_back(self) -> None:
        from webcompy_server.ports import VirtualDOMEvent

        changes: list[str] = []

        @define_component(custom_element_name="test-bind-raw")
        def Page(ctx: ComponentContext) -> Any:
            return Input({"value": "seed", "on_change": changes.append})

        with TestRenderer.render(Page) as result:
            input_node = _find_tag(result.body_node, "INPUT")
            assert input_node.getAttribute("value") == "seed"
            input_node.value = "typed"
            input_node.dispatchEvent(VirtualDOMEvent("input"))
            assert changes == ["typed"]

    def test_raw_signal_value_synchronizes_both_directions(self) -> None:
        from webcompy_server.ports import VirtualDOMEvent

        signal = Signal("seed")
        changes: list[str] = []

        @define_component(custom_element_name="test-bind-raw-signal")
        def Page(ctx: ComponentContext) -> Any:
            return Input({"value": signal, "on_change": changes.append})

        with TestRenderer.render(Page) as result:
            input_node = _find_tag(result.body_node, "INPUT")
            assert input_node.getAttribute("value") == "seed"
            input_node.value = "typed"
            input_node.dispatchEvent(VirtualDOMEvent("input"))
            assert signal.value == "typed"
            assert changes == ["typed"]
            signal.value = "programmatic"
            assert input_node.getAttribute("value") == "programmatic"

    def test_both_modes_rejected(self) -> None:
        field = _required_field()

        @define_component(custom_element_name="test-input-both")
        def Page(ctx: ComponentContext) -> Any:
            return Input({"field": field, "value": "x"})

        with pytest.raises(WebComPyException, match="not both"), TestRenderer.render(Page):
            pass

    def test_unsupported_input_type_rejected(self) -> None:
        @define_component(custom_element_name="test-input-type")
        def Page(ctx: ComponentContext) -> Any:
            return Input({"value": "x", "input_type": "color"})

        with pytest.raises(WebComPyException, match="input_type"), TestRenderer.render(Page):
            pass

    def test_number_input_coerces_per_bind_rules(self) -> None:
        from webcompy_server.ports import VirtualDOMEvent

        field = use_field(Signal(5))

        @define_component(custom_element_name="test-input-number")
        def Page(ctx: ComponentContext) -> Any:
            return Input({"field": field, "input_type": "number"})

        with TestRenderer.render(Page) as result:
            input_node = _find_tag(result.body_node, "INPUT")
            input_node.value = "42"
            input_node.dispatchEvent(VirtualDOMEvent("input"))
            assert field.value.value == 42

    def test_unbound_radio_group_rejected(self) -> None:
        @define_component(custom_element_name="test-group-unbound")
        def Page(ctx: ComponentContext) -> Any:
            return RadioGroup({"options": [{"value": "a"}]})

        with pytest.raises(WebComPyException, match="requires a 'field' or 'value'"), TestRenderer.render(Page):
            pass

    def test_radio_rejects_plain_value(self) -> None:
        from webcompy.ui.headless import Radio

        @define_component(custom_element_name="test-radio-plain-value")
        def Page(ctx: ComponentContext) -> Any:
            return Radio({"value": "a", "option_value": "a", "name": "g"})

        with pytest.raises(WebComPyException, match="shared group Signal"), TestRenderer.render(Page):
            pass


class TestSelectControl:
    """6.2: options rendering and selection binding."""

    def test_select_renders_options_and_reflects_value(self) -> None:
        field = use_field(Signal("b"))

        @define_component(custom_element_name="test-select-basic")
        def Page(ctx: ComponentContext) -> Any:
            return Select(
                {
                    "field": field,
                    "options": [
                        {"value": "a", "label": "Alpha"},
                        {"value": "b", "label": "Beta"},
                    ],
                }
            )

        with TestRenderer.render(Page) as result:
            select_node = _find_tag(result.body_node, "SELECT")
            assert select_node.getAttribute("value") == "b"
            options = _find_all(result.body_node, lambda n: n.nodeName == "OPTION")
            assert [(o.getAttribute("value"), o.textContent) for o in options] == [("a", "Alpha"), ("b", "Beta")]
            assert options[1].getAttribute("selected") == ""
            assert options[0].getAttribute("selected") is None

    def test_select_change_writes_back(self) -> None:
        from webcompy_server.ports import VirtualDOMEvent

        field = use_field(Signal("a"))

        @define_component(custom_element_name="test-select-write")
        def Page(ctx: ComponentContext) -> Any:
            return Select({"field": field, "options": [{"value": "a"}, {"value": "b"}]})

        with TestRenderer.render(Page) as result:
            select_node = _find_tag(result.body_node, "SELECT")
            select_node.value = "b"
            select_node.dispatchEvent(VirtualDOMEvent("change"))
            assert field.value.value == "b"
            select_node.dispatchEvent(VirtualDOMEvent("blur"))
            assert field.touched.value is True


class TestCheckboxAndSwitch:
    """6.2: checkbox checked binding and switch ARIA."""

    def test_checkbox_toggle_writes_back(self) -> None:
        from webcompy_server.ports import VirtualDOMEvent

        field = use_field(Signal(False))

        @define_component(custom_element_name="test-checkbox-toggle")
        def Page(ctx: ComponentContext) -> Any:
            return Checkbox({"field": field, "label": "Agree"})

        with TestRenderer.render(Page) as result:
            body = result.body_node
            label_node = _find_tag(body, "LABEL")
            assert label_node is not None
            input_node = _find_tag(body, "INPUT")
            assert input_node.getAttribute("checked") is None
            input_node.checked = True
            input_node.dispatchEvent(VirtualDOMEvent("change"))
            assert field.value.value is True
            assert input_node.getAttribute("checked") == ""

    def test_switch_exposes_switch_semantics(self) -> None:
        from webcompy_server.ports import VirtualDOMEvent

        field = use_field(Signal(False))

        @define_component(custom_element_name="test-switch-basic")
        def Page(ctx: ComponentContext) -> Any:
            return Switch({"field": field})

        with TestRenderer.render(Page) as result:
            input_node = _find_tag(result.body_node, "INPUT")
            assert input_node.getAttribute("role") == "switch"
            assert input_node.getAttribute("aria-checked") == "false"
            input_node.checked = True
            input_node.dispatchEvent(VirtualDOMEvent("change"))
            assert field.value.value is True
            assert input_node.getAttribute("aria-checked") == "true"

    def test_switch_aria_checked_follows_programmatic_change(self) -> None:
        field = use_field(Signal(True))

        @define_component(custom_element_name="test-switch-reactive")
        def Page(ctx: ComponentContext) -> Any:
            return Switch({"field": field})

        with TestRenderer.render(Page) as result:
            input_node = _find_tag(result.body_node, "INPUT")
            assert input_node.getAttribute("aria-checked") == "true"
            field.value.value = False
            assert input_node.getAttribute("aria-checked") == "false"


class TestRadioGroupControl:
    """6.3: grouped radios from options with generated shared name."""

    def test_structure_and_shared_name(self) -> None:
        field = use_field(Signal("a"))

        @define_component(custom_element_name="test-radio-group-basic")
        def Page(ctx: ComponentContext) -> Any:
            return html.DIV(
                {},
                RadioGroup(
                    {
                        "field": field,
                        "options": [{"value": "a", "label": "Alpha"}, {"value": "b", "label": "Beta"}],
                        "legend": "Pick",
                    }
                ),
            )

        with TestRenderer.render(Page) as result:
            body = result.body_node
            fieldset = _find_tag(body, "FIELDSET")
            legend = _find_tag(body, "LEGEND")
            assert legend.textContent == "Pick"
            radios = _find_all(body, lambda n: n.nodeName == "INPUT" and n.getAttribute("type") == "radio")
            names = {r.getAttribute("name") for r in radios}
            assert len(radios) == 2
            assert len(names) == 1
            assert fieldset.getAttribute("data-state") == "valid"

    def test_group_names_are_instance_unique(self) -> None:
        field = use_field(Signal("a"))

        @define_component(custom_element_name="test-radio-group-two")
        def Page(ctx: ComponentContext) -> Any:
            options = [{"value": "a"}, {"value": "b"}]
            return html.DIV(
                {},
                RadioGroup({"field": field, "options": options}),
                RadioGroup({"field": field, "options": options}),
            )

        var, token = _set_app_ctx()
        try:
            with TestRenderer.render(Page) as result:
                groups = _find_all(result.body_node, lambda n: n.nodeName == "FIELDSET")
                name_0 = _find_all(groups[0], lambda n: n.getAttribute("type") == "radio")[0].getAttribute("name")
                name_1 = _find_all(groups[1], lambda n: n.getAttribute("type") == "radio")[0].getAttribute("name")
                assert name_0 != name_1
        finally:
            var.reset(token)

    def test_selection_writes_back(self) -> None:
        from webcompy_server.ports import VirtualDOMEvent

        field = use_field(Signal("a"))

        @define_component(custom_element_name="test-radio-write")
        def Page(ctx: ComponentContext) -> Any:
            return RadioGroup({"field": field, "options": [{"value": "a"}, {"value": "b"}]})

        with TestRenderer.render(Page) as result:
            radios = _find_all(result.body_node, lambda n: n.getAttribute("type") == "radio")
            checked = [r for r in radios if r.getAttribute("checked") == ""]
            assert [r.getAttribute("value") for r in checked] == ["a"]
            radios[1].checked = True
            radios[1].dispatchEvent(VirtualDOMEvent("change"))
            assert field.value.value == "b"


class TestFormFieldWrapper:
    """6.4: caption, error region, and ARIA wiring end to end."""

    def test_wiring_and_error_gating(self) -> None:
        field = _required_field()

        @define_component(custom_element_name="test-form-field-e2e")
        def Page(ctx: ComponentContext) -> Any:
            return FormField({"field": field, "label": "Name"}, slots={"default": lambda: Input({"field": field})})  # type: ignore[arg-type]

        with TestRenderer.render(Page) as result:
            body = result.body_node
            label_node = _find_tag(body, "LABEL")
            input_node = _find_tag(body, "INPUT")
            error_region = next(n for n in _find_all(body, lambda n: n.getAttribute("role") == "alert"))
            assert label_node.getAttribute("for") == input_node.getAttribute("id")
            assert error_region.getAttribute("id") != input_node.getAttribute("id")
            assert _find_all(error_region, lambda n: n.nodeName == "SPAN") == []
            field.touched.value = True
            messages = [s.textContent for s in _find_all(error_region, lambda n: n.nodeName == "SPAN")]
            assert messages == ["required"]
            assert input_node.getAttribute("aria-invalid") == "true"
            assert input_node.getAttribute("aria-describedby") == error_region.getAttribute("id")
            field.value.value = "filled"
            assert _find_all(error_region, lambda n: n.nodeName == "SPAN") == []
            assert input_node.getAttribute("aria-describedby") is None

    def test_ids_are_distinct_per_instance(self) -> None:
        field_a = _required_field()
        field_b = _required_field()

        @define_component(custom_element_name="test-form-field-two")
        def Page(ctx: ComponentContext) -> Any:
            return html.DIV(
                {},
                FormField({"field": field_a, "label": "A"}, slots={"default": lambda: Input({"field": field_a})}),  # type: ignore[arg-type]
                FormField({"field": field_b, "label": "B"}, slots={"default": lambda: Input({"field": field_b})}),  # type: ignore[arg-type]
            )

        var, token = _set_app_ctx()
        try:
            with TestRenderer.render(Page) as result:
                inputs = _find_all(result.body_node, lambda n: n.nodeName == "INPUT")
                ids = {i.getAttribute("id") for i in inputs}
                assert len(ids) == 2
        finally:
            var.reset(token)

    def test_field_required(self) -> None:
        @define_component(custom_element_name="test-form-field-no-field")
        def Page(ctx: ComponentContext) -> Any:
            return FormField({"label": "A"}, slots={"default": lambda: html.SPAN({})})  # type: ignore[arg-type]

        with pytest.raises(WebComPyException, match="requires a 'field'"), TestRenderer.render(Page):
            pass

    def test_labelless_form_field(self) -> None:
        field = _required_field()

        @define_component(custom_element_name="test-form-field-legendless")
        def Page(ctx: ComponentContext) -> Any:
            return FormField(
                {"field": field},
                slots={  # type: ignore[arg-type]
                    "default": lambda: RadioGroup(
                        {
                            "field": use_field(Signal("a"), validators=[lambda v: None if v else "pick"]),
                            "options": [{"value": "a"}],
                            "legend": "Group",
                        }
                    )
                },
            )

        with TestRenderer.render(Page) as result:
            assert _find_tag(result.body_node, "LABEL") is not None  # radio option label
            assert _find_tag(result.body_node, "LEGEND") is not None


class TestContextConfinement:
    """FormField association ids stay confined to its slot render pass."""

    def test_standalone_control_after_form_field_not_wired(self) -> None:
        field_a = _required_field()
        field_b = _required_field()

        @define_component(custom_element_name="test-ff-confinement")
        def Page(ctx: ComponentContext) -> Any:
            return html.DIV(
                {},
                FormField({"field": field_a, "label": "A"}, slots={"default": lambda: Input({"field": field_a})}),  # type: ignore[arg-type]
                Input({"field": field_b}),
            )

        var, token = _set_app_ctx()
        try:
            with TestRenderer.render(Page) as result:
                inputs = _find_all(result.body_node, lambda n: n.nodeName == "INPUT")
                assert len(inputs) == 2
                field_a.touched.value = True
                field_b.touched.value = True
                error_region = next(n for n in _find_all(result.body_node, lambda n: n.getAttribute("role") == "alert"))
                assert inputs[0].getAttribute("id") is not None
                assert inputs[0].getAttribute("aria-describedby") == error_region.getAttribute("id")
                assert inputs[1].getAttribute("id") is None
                assert inputs[1].getAttribute("aria-describedby") is None
                assert inputs[1].getAttribute("data-state") == "invalid"
        finally:
            var.reset(token)

    def test_themed_standalone_after_form_field_not_wired(self) -> None:
        from webcompy.ui.components import FormField as ThemedFormField
        from webcompy.ui.components import Input as ThemedInput

        field_a = _required_field()
        field_b = _required_field()

        @define_component(custom_element_name="test-ff-confinement-themed")
        def Page(ctx: ComponentContext) -> Any:
            return html.DIV(
                {},
                ThemedFormField(  # type: ignore[call-arg]
                    {"field": field_a, "label": "A"},
                    slots={"default": lambda: ThemedInput({"field": field_a})},  # type: ignore[arg-type]
                ),
                ThemedInput({"field": field_b}),  # type: ignore[call-arg]
            )

        var, token = _set_app_ctx()
        try:
            with TestRenderer.render(Page) as result:
                inputs = _find_all(result.body_node, lambda n: n.nodeName == "INPUT")
                assert len(inputs) == 2
                field_a.touched.value = True
                field_b.touched.value = True
                assert inputs[0].getAttribute("id") is not None
                assert inputs[1].getAttribute("id") is None
                assert inputs[1].getAttribute("aria-describedby") is None
        finally:
            var.reset(token)

    def test_template_path_slotted_control_wired_sibling_isolated(self) -> None:
        from webcompy.di import inject
        from webcompy.di._keys import _COMPONENT_STORE_KEY
        from webcompy.template import render_template

        field = use_field(Signal(""), validators=[lambda v: None if v else "pick"])
        options = [{"value": "a", "label": "A"}]

        @define_component(custom_element_name="test-ff-confinement-template")
        def Page(ctx: ComponentContext) -> Any:
            store = inject(_COMPONENT_STORE_KEY, default=None)
            if store is not None:
                for name, generator in (("FormField", FormField), ("RadioGroup", RadioGroup)):
                    if name not in store.components:
                        store.add_component(name, generator)
            return render_template(
                """
                <div>
                    <form-field :field="field">
                        <radio-group :field="field" :options="options" legend="One" />
                    </form-field>
                    <radio-group :field="field" :options="options" legend="Two" />
                </div>
                """,
                {"field": field, "options": options},
            )

        var, token = _set_app_ctx()
        try:
            with TestRenderer.render(Page) as result:
                fieldsets = _find_all(result.body_node, lambda n: n.nodeName == "FIELDSET")
                assert len(fieldsets) == 2
                field.touched.value = True
                assert fieldsets[0].getAttribute("aria-describedby") is not None
                assert fieldsets[1].getAttribute("aria-describedby") is None
        finally:
            var.reset(token)


class TestDataStateGating:
    """6.5: data-state follows touched+invalid; raw mode reports valid."""

    @pytest.mark.parametrize(
        ("factory", "initial"),
        [
            (lambda field: Input({"field": field}), ""),
            (lambda field: Textarea({"field": field}), ""),
            (lambda field: Select({"field": field, "options": [{"value": ""}, {"value": "x"}]}), ""),
            (lambda field: Checkbox({"field": field}), False),
            (lambda field: Switch({"field": field}), False),
        ],
    )
    def test_gating_on_bound_controls(self, factory: Any, initial: Any) -> None:
        field = use_field(Signal(initial), validators=[lambda v: "required" if not v else None])

        @define_component(custom_element_name="test-gated-control")
        def Page(ctx: ComponentContext) -> Any:
            return html.DIV({}, factory(field))

        with TestRenderer.render(Page) as result:
            root = (
                _find_tag(result.body_node, "INPUT")
                or _find_tag(result.body_node, "TEXTAREA")
                or _find_tag(result.body_node, "SELECT")
            )
            assert root.getAttribute("data-state") == "valid"
            field.touched.value = True
            assert root.getAttribute("data-state") == "invalid"
            field.value.value = "x" if initial == "" else True
            assert root.getAttribute("data-state") == "valid"

    def test_gating_on_radio_group(self) -> None:
        field = use_field(Signal(""), validators=[lambda v: "required" if not v else None])

        @define_component(custom_element_name="test-gated-group")
        def Page(ctx: ComponentContext) -> Any:
            return RadioGroup({"field": field, "options": [{"value": "a"}]})

        with TestRenderer.render(Page) as result:
            fieldset = _find_tag(result.body_node, "FIELDSET")
            assert fieldset.getAttribute("data-state") == "valid"
            field.touched.value = True
            assert fieldset.getAttribute("data-state") == "invalid"

    def test_raw_mode_reports_valid(self) -> None:
        @define_component(custom_element_name="test-raw-valid")
        def Page(ctx: ComponentContext) -> Any:
            return html.DIV({}, Input({"value": "x"}), Checkbox({"value": False}))

        with TestRenderer.render(Page) as result:
            for node in _find_all(result.body_node, lambda n: n.nodeName == "INPUT"):
                assert node.getAttribute("data-state") == "valid"


class TestImportPaths:
    """5.3: the two-layer layout resolves through all three import paths."""

    def test_three_import_paths(self) -> None:
        import webcompy.ui as ui
        from webcompy.ui import components, headless

        for name in ("Input", "Textarea", "Select", "Checkbox", "Switch", "Radio", "RadioGroup", "FormField"):
            assert getattr(headless, name) is not getattr(components, name), name
            assert getattr(ui, name) is getattr(components, name), name

    def test_css_styles_are_layered(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        css = (root / "packages/webcompy/src/webcompy/ui/_styles/primitives.css").read_text(encoding="utf-8")
        assert ".webcompy-input:focus-visible" in css
        assert '.webcompy-input[data-state="invalid"]' in css
        assert "var(--color-danger)" in css
