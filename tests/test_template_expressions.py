from __future__ import annotations

import pytest

from webcompy.components import define_component
from webcompy.exception import WebComPyException
from webcompy.signal import Computed, Signal
from webcompy.template import render_template
from webcompy.template._binder import bind_children, bind_element
from webcompy.template._expression import compile_expression, evaluate, resolve_scope
from webcompy.template._parser import parse_template
from webcompy_testing import TestRenderer


def _eval(source: str, ctx: dict) -> object:
    plan = compile_expression(source)
    scope = resolve_scope(plan, ctx)
    return evaluate(plan, scope)


class TestWhitelistValidation:
    def test_comprehension_rejected(self):
        with pytest.raises(WebComPyException, match="not allowed"):
            compile_expression("[x for x in items]")

    def test_lambda_rejected(self):
        with pytest.raises(WebComPyException, match="not allowed"):
            compile_expression("(lambda: 1)()")

    def test_walrus_rejected(self):
        with pytest.raises(WebComPyException):
            compile_expression("(x := 1)")

    def test_dunder_attribute_rejected(self):
        with pytest.raises(WebComPyException, match="_"):
            compile_expression("x.__class__")

    def test_private_method_rejected(self):
        with pytest.raises(WebComPyException, match="_"):
            compile_expression("x._secret()")

    def test_syntax_error_raises(self):
        with pytest.raises(WebComPyException, match="Invalid template expression"):
            compile_expression("count +")


class TestFilterBehavior:
    def test_filter_chain(self):
        assert _eval("name | trim | upper", {"name": "  alice  "}) == "ALICE"

    def test_bitwise_or_fallback(self):
        assert _eval("flags | mask", {"flags": 0b1100, "mask": 0b1010}) == 0b1110

    def test_registry_precedence_over_context(self):
        assert _eval("name | upper", {"name": "alice", "upper": lambda v: "WRONG"}) == "ALICE"

    def test_method_call(self):
        assert _eval("name.upper()", {"name": "alice"}) == "ALICE"

    def test_method_call_with_args(self):
        assert _eval("text.replace('a', 'b')", {"text": "aaa"}) == "bbb"

    def test_default_filter_on_none(self):
        assert _eval("missing_val | default('fallback')", {"missing_val": None}) == "fallback"


class TestInvalidIfExpression:
    def test_invalid_if_condition_raises_at_bind(self):
        roots = parse_template("{% if a >> > b %}yes{% endif %}")
        with pytest.raises(WebComPyException):
            bind_children(roots, {"a": 1, "b": 2})

    def test_invalid_for_iterable_raises_at_bind(self):
        roots = parse_template("{% for x in items[ %}<p>{{ x }}</p>{% endfor %}")
        with pytest.raises(WebComPyException):
            bind_children(roots, {"items": [1]})


class TestReactiveExpressionText:
    def test_text_expression_updates_on_signal_change(self):
        captured: dict[str, Signal] = {}

        @define_component()
        def PageWithCapture(context):
            count = Signal(5)
            captured["count"] = count
            return render_template(
                '<span data-testid="v">{{ count + 1 }}</span>',
                {"count": count},
            )

        with TestRenderer.render(PageWithCapture) as result:
            el = result.find_by_attribute("data-testid", "v")
            assert el is not None
            assert el.textContent == "6"
            captured["count"].value = 10
            assert el.textContent == "11"

    def test_non_signal_expression_creates_no_computed(self):
        roots = parse_template("<p>{{ a + b }}</p>")
        children = bind_children(roots, {"a": 1, "b": 2})
        assert len(children) == 1
        p = children[0]
        text_child = p._children[0]
        assert not isinstance(text_child, Computed)

    def test_plain_path_passes_signal_through(self):
        sig = Signal(5)
        roots = parse_template("<p>{{ count }}</p>")
        children = bind_children(roots, {"count": sig})
        p = children[0]
        text_child = p._children[0]
        assert not isinstance(text_child, Computed)
        assert getattr(text_child, "_text", None) is sig


class TestReactiveExpressionFor:
    def test_for_slice_updates_on_list_mutation(self):
        captured: dict[str, object] = {}

        @define_component()
        def TemplateExpressionPage(context):
            from webcompy.signal import use_reactive_list

            items = use_reactive_list(lambda: [1, 2, 3, 4])
            captured["items"] = items
            return render_template(
                '<ul>{% for item in items[:3] %}<li data-testid="li">{{ item }}</li>{% endfor %}</ul>',
                {"items": items},
            )

        with TestRenderer.render(TemplateExpressionPage) as result:
            lis = result.query_selector_all("li")
            assert [li.textContent for li in lis] == ["1", "2", "3"]
            items = captured["items"]
            assert hasattr(items, "pop")
            items.pop(0)
            lis = result.query_selector_all("li")
            assert [li.textContent for li in lis] == ["2", "3", "4"]


class TestReactiveExpressionAttribute:
    def test_attr_expression_creates_computed(self):
        ratio = Signal(0.5)
        roots = parse_template('<div style="width: {{ ratio * 100 }}%"></div>')
        el = bind_element(roots[0], {"ratio": ratio})
        style_value = el._attrs["style"]
        assert isinstance(style_value, Computed)
        assert style_value.value == "width: 50.0%"
        ratio.value = 0.75
        assert style_value.value == "width: 75.0%"

    def test_attr_expression_static_without_signal(self):
        roots = parse_template('<div title="{{ 1 + 2 }}"></div>')
        el = bind_element(roots[0], {})
        assert el._attrs["title"] == "3"
