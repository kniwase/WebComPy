from __future__ import annotations

import html as html_module
import json
import re

from webcompy.components import define_component
from webcompy.signal import ReactiveList, Signal, use_state
from webcompy.template import render_template
from webcompy_server.ports import VirtualDOMEvent
from webcompy_testing import TestRenderer, create_test_app, render_app_html


@define_component
def _TemplateTextRoot(context):
    name = use_state(lambda: "Alice")
    return render_template(
        """
        <div>
            <p>Hello {{ name }}</p>
        </div>
        """,
        locals(),
    )


@define_component
def _TemplateAttrRoot(context):
    cls = use_state(lambda: "active")
    return render_template(
        '<p class="card {{ cls }}">x</p>',
        locals(),
    )


def _generate(root):
    app = create_test_app(root_component=root)
    return render_app_html(
        app,
        app_package_name="test_pkg",
        dev_mode=False,
        prerender=True,
        wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
    )


_HYDRATION_DATA_RE = re.compile(
    r'<script type="application/json" id="__webcompy_data__">(.*?)</script>',
    re.DOTALL,
)


def _read_payload(html_content: str) -> dict | None:
    match = _HYDRATION_DATA_RE.search(html_content)
    if match is None:
        return None
    return json.loads(html_module.unescape(match.group(1)))


class TestTemplateSSR:
    def test_text_interpolation_in_ssr(self):
        html_str = _generate(_TemplateTextRoot)
        assert "<div" in html_str
        assert "<p" in html_str
        assert "Hello" in html_str
        assert "Alice" in html_str

    def test_attribute_interpolation_in_ssr(self):
        html_str = _generate(_TemplateAttrRoot)
        assert "<p" in html_str
        assert "card" in html_str
        assert "active" in html_str

    def test_ssr_payload_contains_transferred_signals(self):
        html_str = _generate(_TemplateTextRoot)
        payload = _read_payload(html_str)
        assert payload is not None, "Hydration payload script not found in SSR HTML"
        assert "signals" in payload
        assert isinstance(payload["signals"], dict)
        assert len(payload["signals"]) > 0, "Expected at least one component's signals in payload"


class TestTemplateTestRenderer:
    def test_signal_text_updates(self):
        @define_component
        def TemplatePage(context):
            count = Signal(0)
            return render_template(
                """
                <div>
                    <span data-testid="count">{{ count }}</span>
                    <button data-testid="inc" @click="increment">+</button>
                </div>
                """,
                {
                    "count": count,
                    "increment": lambda _: setattr(count, "value", count.value + 1),
                },
            )

        with TestRenderer.render(TemplatePage) as result:
            count_el = result.find_by_attribute("data-testid", "count")
            assert count_el is not None
            assert count_el.textContent == "0"
            btn = result.find_by_attribute("data-testid", "inc")
            assert btn is not None
            btn.dispatchEvent(VirtualDOMEvent("click"))
            assert count_el.textContent == "1"

    def test_prerendered_text_node_present(self):
        @define_component
        def StaticTemplatePage(context):
            return render_template(
                "<p data-testid='msg'>hello</p>",
                {},
            )

        with TestRenderer.render(StaticTemplatePage) as result:
            assert "hello" in result.to_html()
            assert 'data-testid="msg"' in result.to_html()


class TestTemplateHydrationAdoption:
    """Verify that TextElement instances produced by `render_template` for
    Signal-valued `{{ }}` interpolation adopt an existing prerendered DOM
    text node (i.e. `__webcompy_prerendered_node__` is honored) and remain
    reactive after adoption.
    """

    def test_signal_text_node_adopts_prerendered_node(self, fake_browser_full):
        from tests.conftest import FakeDOMNode
        from webcompy.elements.types._element import Element as WebCompElement
        from webcompy.template._binder import bind_element
        from webcompy.template._parser import parse_template

        class _FakeRootElement(WebCompElement):
            _get_belonging_component = lambda self: ""
            _get_belonging_components = lambda self: ()

        sig = Signal("hello")
        template_roots = parse_template("<p>{{ v }}</p>")
        element = bind_element(template_roots[0], {"v": sig})
        text_el = element._children[0]

        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._event_handlers_added = {}
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        text_el._parent = parent
        text_el._node_idx = 0

        existing_node = FakeDOMNode("#text", text_content="stale_from_ssr")
        existing_node.__webcompy_prerendered_node__ = True
        parent._node_cache.appendChild(existing_node)

        node = text_el._init_node()
        assert node is existing_node
        assert text_el._mounted is True
        assert node.textContent == "hello"

        sig.value = "world"
        assert text_el._get_node().textContent == "world"


class TestTemplateControlFlowSSR:
    def test_render_app_html_with_if(self):
        @define_component
        def IfPage(context):
            show = Signal(True)
            return render_template(
                "<div data-testid='if-root'>{% if show %}A{% else %}B{% endif %}</div>",
                {"show": show},
            )

        html = _generate(IfPage)
        assert "A" in html
        assert 'data-testid="if-root"' in html

    def test_render_app_html_with_for(self):
        @define_component
        def ForPage(context):
            items = ReactiveList(["x", "y", "z"])
            return render_template(
                "<ul data-testid='for-root'>{% for item in items %}<li data-testid='li'>{{ item }}</li>{% endfor %}</ul>",
                {"items": items},
            )

        html = _generate(ForPage)
        assert 'data-testid="li"' in html
        assert "x" in html
        assert "y" in html
        assert "z" in html

    def test_render_app_html_with_nested_control_flow(self):
        @define_component
        def NestedPage(context):
            items = [
                {"name": "a", "visible": True},
                {"name": "b", "visible": False},
                {"name": "c", "visible": True},
            ]
            return render_template(
                "<ul>{% for item in items %}{% if item.visible %}<li>{{ item.name }}</li>{% endif %}{% endfor %}</ul>",
                {"items": items},
            )

        html = _generate(NestedPage)
        assert "a" in html
        assert "c" in html
        assert "b" not in html or "b</li>" not in html

    def test_render_app_html_with_dict_kv(self):
        @define_component
        def DictPage(context):
            return render_template(
                "<ul>{% for k, v in d %}<li>{{ k }}={{ v }}</li>{% endfor %}</ul>",
                {"d": {"a": 1, "b": 2}},
            )

        html = _generate(DictPage)
        assert "a" in html and "1" in html
        assert "b" in html and "2" in html


class TestTemplateControlFlowPrerenderedFlags:
    def test_if_branch_renders_correct_branch(self):
        @define_component
        def BranchPage(context):
            flag = True
            return render_template(
                "<div>{% if flag %}visible{% else %}hidden{% endif %}</div>",
                {"flag": flag},
            )

        with TestRenderer.render(BranchPage) as result:
            html = result.to_html()
            assert "visible" in html
            assert "hidden" not in html

    def test_for_loop_renders_all_iterations(self):
        @define_component
        def LoopPage(context):
            items = ["a", "b", "c"]
            return render_template(
                "<ul>{% for item in items %}<li>{{ item }}</li>{% endfor %}</ul>",
                {"items": items},
            )

        with TestRenderer.render(LoopPage) as result:
            html = result.to_html()
            assert "<li" in html
            assert html.count("<li") == 3
            assert "a" in html and "b" in html and "c" in html


class TestComponentTagSSR:
    """SSR-time rendering of component tags produces the component's output."""

    def test_ssr_includes_component_template_output(self):
        @define_component
        def GreetingCard(context):
            name = context.props.get("name", "")
            return render_template(f"<span data-testid='name'>Hi {name}</span>")

        @define_component
        def GreetingPage(context):
            return render_template(
                "<div><greeting-card name='Alice' /></div>",
            )

        app = create_test_app(root_component=GreetingPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "<span" in html_str
        assert "Hi Alice" in html_str
        assert 'data-testid="name"' in html_str


class TestComponentTagTestRenderer:
    """TestRenderer should expose component-tag-rendered DOM nodes."""

    def test_component_tag_renders_into_test_renderer(self):
        @define_component
        def InfoBadge(context):
            label = context.props.get("label", "")
            return render_template(f"<span data-testid='badge'>{label}</span>")

        @define_component
        def BadgePage(context):
            return render_template(
                "<div><info-badge label='ready' /></div>",
            )

        with TestRenderer.render(BadgePage) as result:
            html = result.to_html()
            assert "<span" in html
            assert "ready" in html
            assert 'data-testid="badge"' in html
            badge = result.find_by_attribute("data-testid", "badge")
            assert badge is not None
            assert badge.textContent == "ready"


@define_component
def _ExprRoot(context):
    count = use_state(lambda: 5)
    name = use_state(lambda: "alice")
    items = use_state(lambda: ["a", "b", "c"])
    return render_template(
        """
        <div>
            <p data-testid="arith">{{ count + 1 }}</p>
            <p data-testid="filter">{{ name | upper }}</p>
            <p data-testid="subscript">{{ items[0] }}</p>
            <p data-testid="slice">{{ items[:2] | join(", ") }}</p>
        </div>
        """,
        locals(),
    )


class TestExprSSR:
    def test_expression_renders_arithmetic(self):
        with TestRenderer.render(_ExprRoot) as result:
            el = result.find_by_attribute("data-testid", "arith")
            assert el is not None
            assert el.textContent == "6"

    def test_expression_renders_filter(self):
        with TestRenderer.render(_ExprRoot) as result:
            el = result.find_by_attribute("data-testid", "filter")
            assert el is not None
            assert el.textContent == "ALICE"

    def test_expression_renders_subscript(self):
        with TestRenderer.render(_ExprRoot) as result:
            el = result.find_by_attribute("data-testid", "subscript")
            assert el is not None
            assert el.textContent == "a"

    def test_expression_renders_slice_with_filter(self):
        with TestRenderer.render(_ExprRoot) as result:
            el = result.find_by_attribute("data-testid", "slice")
            assert el is not None
            assert el.textContent == "a, b"


@define_component
def _CommentRawRoot(context):
    return render_template(
        """
        <div>
            <p data-testid="comment">Hello{# comment #} World</p>
            <p data-testid="raw">{% raw %}{{ literal }}{% endraw %}</p>
        </div>
        """,
    )


class TestCommentRawSSR:
    def test_comment_not_in_output(self):
        with TestRenderer.render(_CommentRawRoot) as result:
            el = result.find_by_attribute("data-testid", "comment")
            assert el is not None
            assert el.textContent == "Hello World"

    def test_raw_block_preserves_literal_braces(self):
        with TestRenderer.render(_CommentRawRoot) as result:
            el = result.find_by_attribute("data-testid", "raw")
            assert el is not None
            assert el.textContent == "{{ literal }}"

    def test_comment_inside_raw_preserved(self):
        @define_component
        def RawCommentPage(context):
            return render_template(
                '<p data-testid="rc">{% raw %}{# not a comment #}{% endraw %}</p>',
            )

        with TestRenderer.render(RawCommentPage) as result:
            el = result.find_by_attribute("data-testid", "rc")
            assert el is not None
            assert el.textContent == "{# not a comment #}"

    def test_raw_block_literal_directive(self):
        @define_component
        def RawDirectivePage(context):
            return render_template(
                '<p data-testid="rd">{% raw %}{% if x %}{% endraw %}</p>',
            )

        with TestRenderer.render(RawDirectivePage) as result:
            el = result.find_by_attribute("data-testid", "rd")
            assert el is not None
            assert el.textContent == "{% if x %}"

    def test_tags_inside_raw_still_parse(self):
        @define_component
        def RawTagsPage(context):
            return render_template(
                '<div data-testid="rt">{% raw %}<b>{{ x }}</b>{% endraw %}</div>',
            )

        with TestRenderer.render(RawTagsPage) as result:
            el = result.find_by_attribute("data-testid", "rt")
            assert el is not None
            html_out = result.to_html()
            assert "<b " in html_out or "<b>" in html_out
            assert "{{ x }}</b>" in html_out
