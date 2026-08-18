from __future__ import annotations

import re
import sys
import types

import pytest

from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy.components import define_component
from webcompy.di import inject
from webcompy.elements import html
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
from webcompy.router import Router
from webcompy.router._lazy import lazy
from webcompy_server import configure_server_context
from webcompy_server._html import generate_html


async def _render_html(app: WebComPyApp, path: str) -> str:
    ctx = app.create_render_context(path)
    try:
        scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
        await scheduler.await_pending()
        return await generate_html(
            ctx,
            app_package_name="iso_app",
            dev_mode=False,
            prerender=True,
            wheel_filename="iso.whl",
        )
    finally:
        ctx.dispose()


def _make_isolation_app() -> WebComPyApp:
    """Build an app whose nested layout route lazily imports a styled component.

    The layout module is only reachable through the nested ``/docs`` route, so it
    is first imported while a render context is active (via the RouterView
    preload) — the exact pattern that previously left the imported component's
    generator invisible to every later render context.
    """

    @define_component("iso-sidebar")
    def IsoSidebar(context):
        return html.DIV({}, "sidebar")

    IsoSidebar.scoped_style = {".iso-sidebar": {"color": "red"}}

    sidebar_mod = types.ModuleType("iso_sidebar_mod")
    sidebar_mod.IsoSidebar = IsoSidebar
    sys.modules["iso_sidebar_mod"] = sidebar_mod

    layout_mod = types.ModuleType("iso_layout_mod")
    exec(
        "from webcompy.components import define_component\n"
        "from webcompy.elements import html\n"
        "from iso_sidebar_mod import IsoSidebar\n"
        "@define_component('iso-layout')\n"
        "def IsoLayout(context):\n"
        "    return html.DIV({}, IsoSidebar(None))\n"
        "IsoLayout.scoped_style = {'.iso-layout': {'color': 'blue'}}\n",
        layout_mod.__dict__,
    )
    sys.modules["iso_layout_mod"] = layout_mod

    @define_component("iso-home")
    def IsoHome(context):
        return html.DIV({}, "home")

    @define_component("iso-child")
    def IsoChild(context):
        return html.DIV({}, "child")

    router = Router(
        {"path": "/", "component": IsoHome},
        {
            "path": "/docs",
            "component": lazy("iso_layout_mod:IsoLayout", __file__),
            "children": [{"path": "child", "component": IsoChild}],
        },
        mode="history",
        base_url="",
    )
    app = WebComPyApp(root_component=IsoHome, router=router, config=WebComPyAppConfig(base_url="/"))
    configure_server_context(app)
    return app


def _style_cids(html: str) -> set[str]:
    return set(re.findall(r'data-webcompy-cid="([^"]+)"', html))


@pytest.mark.asyncio
async def test_lazy_layout_component_registered_in_later_render_contexts():
    app = _make_isolation_app()

    await _render_html(app, "/")

    docs_html = await _render_html(app, "/docs/child")
    assert re.search(r"\.iso-sidebar\[webcompy-cid-", docs_html), (
        "the sidebar's scoped style must appear on a page generated after the "
        "layout module was first imported with an active DI scope"
    )
    assert re.search(r"\.iso-layout\[webcompy-cid-", docs_html)


@pytest.mark.asyncio
async def test_identical_style_sets_across_render_contexts():
    app = _make_isolation_app()

    await _render_html(app, "/")

    docs_html_a = await _render_html(app, "/docs/child")
    docs_html_b = await _render_html(app, "/docs/child")
    assert _style_cids(docs_html_a) == _style_cids(docs_html_b)
    assert ".iso-sidebar[webcompy-cid-" in docs_html_a
    assert ".iso-sidebar[webcompy-cid-" in docs_html_b
