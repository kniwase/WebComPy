from __future__ import annotations

import html as html_module
import json
import re

from webcompy.components import define_component
from webcompy.signal import Signal, use_state
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
