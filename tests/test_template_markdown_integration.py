from __future__ import annotations

import html as html_module
import json
import re
from typing import Any

from webcompy.components import define_component
from webcompy.di._scope import DIScope
from webcompy.elements import html
from webcompy.ports._keys import MARKDOWN_PORT_KEY
from webcompy.ports._markdown import MarkdownPort
from webcompy.signal import Signal, use_reactive_list, use_state
from webcompy.template import render_markdown
from webcompy.template._markdown_default import DefaultMarkdownParser
from webcompy_server.ports import VirtualDOMEvent
from webcompy_testing import TestRenderer, create_test_app, render_app_html


def _markdown_parent_scope(parser: MarkdownPort | None = None) -> DIScope:
    scope = DIScope()
    scope.provide(MARKDOWN_PORT_KEY, parser or DefaultMarkdownParser())
    return scope


_HYDRATION_DATA_RE = re.compile(
    r'<script type="application/json" id="__webcompy_data__">(.*?)</script>',
    re.DOTALL,
)


def _read_payload(html_content: str) -> dict | None:
    match = _HYDRATION_DATA_RE.search(html_content)
    if match is None:
        return None
    return json.loads(html_module.unescape(match.group(1)))


class TestMarkdownComponentWithLocals:
    def test_render_markdown_with_locals_inside_define_component(self):
        @define_component
        def MarkdownPage(context):
            name = use_state(lambda: "World")
            return html.ARTICLE(
                {},
                render_markdown(
                    "# Hello {{ name }}",
                    locals(),
                ),
            )

        result = TestRenderer.render(MarkdownPage, parent_scope=_markdown_parent_scope())
        try:
            html_str = result.to_html()
            assert "<article" in html_str
            assert "<h1" in html_str
            assert "Hello" in html_str
            assert "World" in html_str
            assert result.find_by_text("Hello World") is not None
            h1 = result.query_selector("h1")
            assert h1 is not None
            assert "Hi" not in html_str
        finally:
            result.close()


class TestMarkdownReactiveUpdate:
    def test_signal_change_updates_markdown_text(self):
        @define_component
        def ReactiveMarkdownPage(context):
            count = use_state(lambda: 0)
            return html.DIV(
                {},
                render_markdown(
                    "# Count {{ count }}",
                    {
                        "count": count,
                        "increment": lambda _: setattr(count, "value", count.value + 1),
                    },
                ),
                html.BUTTON(
                    {
                        "@click": lambda _: setattr(count, "value", count.value + 1),
                        "data-testid": "inc",
                    },
                    "+",
                ),
            )

        result = TestRenderer.render(ReactiveMarkdownPage, parent_scope=_markdown_parent_scope())
        try:
            h1 = result.query_selector("h1")
            assert h1 is not None
            assert h1.textContent == "Count 0"
            btn = result.find_by_attribute("data-testid", "inc")
            assert btn is not None
            btn.dispatchEvent(VirtualDOMEvent("click"))
            assert h1.textContent == "Count 1"
            btn.dispatchEvent(VirtualDOMEvent("click"))
            assert h1.textContent == "Count 2"
        finally:
            result.close()


class TestMarkdownForLoopReactiveItems:
    def test_reactive_list_in_markdown_for_loop_produces_single_ul(self):
        @define_component
        def MarkdownForPage(context):
            items = use_reactive_list(lambda: ["alpha", "beta", "gamma"])
            return html.DIV(
                {},
                render_markdown(
                    "{% for item in items %}\n- {{ item }}\n{% endfor %}",
                    locals(),
                ),
                html.BUTTON(
                    {
                        "@click": lambda _: items.append("delta"),
                        "data-testid": "add",
                    },
                    "+",
                ),
            )

        result = TestRenderer.render(MarkdownForPage, parent_scope=_markdown_parent_scope())
        try:
            html_str = result.to_html()
            assert html_str.count("<ul") == 1
            assert html_str.count("<li") == 3
            assert "alpha" in html_str
            assert "beta" in html_str
            assert "gamma" in html_str
            assert "delta" not in html_str

            btn = result.find_by_attribute("data-testid", "add")
            assert btn is not None
            btn.dispatchEvent(VirtualDOMEvent("click"))
            html_str = result.to_html()
            assert html_str.count("<ul") == 1
            assert html_str.count("<li") == 4
            assert "delta" in html_str
        finally:
            result.close()


class TestMarkdownDynamicProps:
    def test_kebab_dynamic_prop_passes_signal_to_component(self):
        captured: dict[str, Any] = {}

        @define_component
        def MyCard(context):
            captured["props"] = dict(context.props)
            n = context.props.get("count", 0)
            if hasattr(n, "value"):
                n = n.value
            return html.SPAN({"data-testid": "card"}, f"count={n}")

        @define_component
        def DynamicPropPage(context):
            sig = Signal(7)
            return html.DIV(
                {},
                render_markdown(
                    '<my-card :count="n" />',
                    {"n": sig},
                ),
            )

        result = TestRenderer.render(DynamicPropPage, parent_scope=_markdown_parent_scope())
        try:
            assert "count" in captured["props"]
            prop_value = captured["props"]["count"]
            assert isinstance(prop_value, Signal)
            assert prop_value.value == 7
            card = result.find_by_attribute("data-testid", "card")
            assert card is not None
            assert card.textContent == "count=7"
        finally:
            result.close()

    def test_kebab_dynamic_prop_resolves_plain_value(self):
        captured: dict[str, Any] = {}

        @define_component
        def StaticCard(context):
            captured["props"] = dict(context.props)
            n = context.props.get("count", 0)
            if hasattr(n, "value"):
                n = n.value
            return html.SPAN({"data-testid": "card"}, f"count={n}")

        @define_component
        def PlainPropPage(context):
            return html.DIV(
                {},
                render_markdown(
                    '<static-card :count="n" />',
                    {"n": 42},
                ),
            )

        result = TestRenderer.render(PlainPropPage, parent_scope=_markdown_parent_scope())
        try:
            assert captured["props"] == {"count": 42}
            card = result.find_by_attribute("data-testid", "card")
            assert card is not None
            assert card.textContent == "count=42"
        finally:
            result.close()


class TestMarkdownSSR:
    def test_ssr_contains_rendered_markdown_html(self):
        @define_component
        def MarkdownSSRPage(context):
            return html.ARTICLE(
                {},
                render_markdown("# SSR Title", {}),
            )

        app = create_test_app(root_component=MarkdownSSRPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        assert "<article" in html_str
        assert "<h1" in html_str
        assert "SSR Title" in html_str

    def test_ssr_payload_includes_hydration_script(self):
        @define_component
        def MarkdownPayloadPage(context):
            return html.SECTION(
                {},
                render_markdown("## Hydration Section", {}),
            )

        app = create_test_app(root_component=MarkdownPayloadPage)
        html_str = render_app_html(
            app,
            app_package_name="test_pkg",
            dev_mode=False,
            prerender=True,
            wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
        )
        payload = _read_payload(html_str)
        assert payload is not None, "Hydration payload script not found in SSR HTML"
        assert "Hydration Section" in html_str


class TestCustomMarkdownParserInjection:
    def test_custom_parser_via_parent_scope_replaces_default(self):
        class _CustomMarkdownParser(MarkdownPort):
            def __init__(self) -> None:
                self.invocations = 0

            def render(self, source: str) -> str:
                self.invocations += 1
                return f"<div class='custom-md'>{source}</div>"

        custom = _CustomMarkdownParser()

        @define_component
        def CustomParserPage(context):
            return html.SECTION(
                {},
                render_markdown("# Title", {}),
            )

        result = TestRenderer.render(CustomParserPage, parent_scope=_markdown_parent_scope(custom))
        try:
            html_str = result.to_html()
            assert "custom-md" in html_str
            assert "# Title" in html_str
            assert "<h1" not in html_str
            assert custom.invocations == 1
        finally:
            result.close()

    def test_custom_parser_via_app_provide_is_visible_in_render_context(self):
        class _AppProvideCustomParser(MarkdownPort):
            def render(self, source: str) -> str:
                return f"<app-provide-md>{source}</app-provide-md>"

        from webcompy.app._app import WebComPyApp
        from webcompy.app._config import WebComPyAppConfig
        from webcompy_server import configure_server_context

        @define_component
        def AppProvidePage(context):
            return html.HEADER({}, render_markdown("# App Provide", {}))

        app = WebComPyApp(root_component=AppProvidePage, config=WebComPyAppConfig())
        configure_server_context(app)
        custom = _AppProvideCustomParser()
        app.provide(MARKDOWN_PORT_KEY, custom)

        ctx = app.create_render_context("/", initial_theme=None)
        try:
            injected = ctx.di_scope.inject(MARKDOWN_PORT_KEY)
            assert injected is custom
            assert injected is not DefaultMarkdownParser()
            assert isinstance(injected, MarkdownPort)
            assert injected.render("# x") == "<app-provide-md># x</app-provide-md>"
        finally:
            ctx.dispose()


class TestMarkdownForMixedBodies:
    def test_list_body_and_non_list_body_in_same_document(self):
        @define_component
        def MixedForPage(context):
            items = ["a", "b"]
            return html.ARTICLE(
                {},
                render_markdown(
                    "# Title\n\n"
                    "{% for item in items %}\n- {{ item }}\n{% endfor %}\n\n"
                    "{% for n in nums %}\n## {{ n }}\n{% endfor %}",
                    {"items": items, "nums": [1, 2]},
                ),
            )

        result = TestRenderer.render(MixedForPage, parent_scope=_markdown_parent_scope())
        try:
            html_str = result.to_html()
            assert html_str.count("<ul") == 1
            assert html_str.count("<li") == 2
            assert html_str.count("<h2") == 2
        finally:
            result.close()
