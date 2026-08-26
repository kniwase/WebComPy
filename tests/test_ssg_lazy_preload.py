from __future__ import annotations

import sys
import types
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.components import define_component
from webcompy.elements import html
from webcompy.router._lazy import lazy
from webcompy.router._router import Router
from webcompy_cli._build import BuildArtifacts
from webcompy_cli.config._build_config import WebComPyBuildConfig


def _setup_app_pkg(tmp_path: Path):
    pkg = tmp_path / "app"
    pkg.mkdir()
    mod_path = pkg / "_app_mod.py"
    mod_path.write_text("app = None\n")
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ephemeral_app", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    build_config = WebComPyBuildConfig(app_module=mod)
    return pkg, build_config


def _make_artifacts(tmp_path: Path) -> BuildArtifacts:
    return BuildArtifacts(
        app_version="test-version",
        wheel_filename="test.whl",
        app_package_files={"test.whl": (b"x", "application/zip")},
        resource_allow_list=None,
        dist_dir=tmp_path / "dist",
        dev_mode=False,
    )


class _FakeServingApp:
    def __init__(self, artifacts: BuildArtifacts) -> None:
        self.artifacts = artifacts
        self.asgi = None
        self.html_generator = None
        self.hash_cache: list[str] = []


def _run_generate(
    build_config: WebComPyBuildConfig,
    app: WebComPyApp,
    artifacts: BuildArtifacts,
    check_first_request: Callable[[], bool] | None = None,
) -> bool | None:
    from webcompy_cli._generate import generate_static_site

    pkg = build_config.app_package_path
    saved_argv = sys.argv
    sys.argv = ["webcompy", "generate"]
    fake_mod = types.ModuleType("fake_app_mod")
    fake_mod.__file__ = str(pkg / "_app_mod.py")
    fake_mod.app = app
    sys.modules["fake_app_mod"] = fake_mod

    first_request_seen = None

    async def _trivial_asgi(scope, receive, send):
        if scope["type"] != "http":
            return
        nonlocal first_request_seen
        if check_first_request is not None and first_request_seen is None:
            first_request_seen = check_first_request()
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/html")],
            }
        )
        await send({"type": "http.response.body", "body": b"<html></html>"})

    fake_serving = _FakeServingApp(artifacts)
    fake_serving.asgi = _trivial_asgi

    try:
        with (
            patch(
                "webcompy_cli._generate.create_asgi_app",
                return_value=fake_serving,
            ),
            patch(
                "webcompy_cli._generate.discover_config",
                return_value=build_config,
            ),
            patch(
                "webcompy_cli._generate.get_static_files",
                return_value=(),
            ),
            patch(
                "webcompy.ui._styles.get_styles_files",
                return_value={},
                create=True,
            ),
        ):
            import asyncio

            asyncio.run(generate_static_site(app=app))
    finally:
        sys.modules.pop("fake_app_mod", None)
        sys.argv = saved_argv

    return first_request_seen


class TestGenerateLazyRoutePreload:
    def test_lazy_route_is_preloaded_before_route_fetching(self, tmp_path: Path) -> None:
        pkg, build_config = _setup_app_pkg(tmp_path)
        artifacts = _make_artifacts(tmp_path)

        @define_component()
        def LazyPage(ctx):

            return html.DIV({})

        comp = LazyPage
        comp.scoped_style = {".lazy-page": {"color": "red"}}
        fake_module = types.ModuleType("lazy_page_module")
        fake_module.LazyPage = comp
        sys.modules["lazy_page_module"] = fake_module

        lazy_gen = lazy("lazy_page_module:LazyPage", __file__)
        router = Router(
            {"path": "/", "component": lazy_gen},
            mode="history",
            preload=False,
        )
        app = WebComPyApp(
            root_component=lambda _: None,
            router=router,
            config=WebComPyAppConfig(base_url="/"),
        )

        assert lazy_gen._resolved is None

        first_request_seen_resolved = _run_generate(
            build_config,
            app,
            artifacts,
            check_first_request=lambda: lazy_gen._resolved is not None,
        )

        assert lazy_gen._resolved is comp
        assert first_request_seen_resolved is True
        assert "color" in lazy_gen.scoped_style
        assert "webcompy-cid" in lazy_gen.scoped_style
        assert (pkg / "dist" / "index.html").exists()

    def test_eager_route_does_not_require_preload(self, tmp_path: Path) -> None:
        pkg, build_config = _setup_app_pkg(tmp_path)
        artifacts = _make_artifacts(tmp_path)

        @define_component()
        def EagerPage(ctx):

            return html.DIV({})

        comp = EagerPage
        router = Router(
            {"path": "/", "component": comp},
            mode="history",
            preload=False,
        )
        app = WebComPyApp(
            root_component=lambda _: None,
            router=router,
            config=WebComPyAppConfig(base_url="/"),
        )

        _run_generate(build_config, app, artifacts)

        assert (pkg / "dist" / "index.html").exists()

    def test_nested_lazy_layout_with_styled_import_preloaded(self, tmp_path: Path) -> None:
        """A nested layout route (not present in the flattened route list) must
        still be pre-resolved before route fetching, along with the styled
        component it imports."""
        _pkg, build_config = _setup_app_pkg(tmp_path)
        artifacts = _make_artifacts(tmp_path)

        sidebar_mod = types.ModuleType("nested_sidebar_mod")

        @define_component()
        def NestedSidebar(ctx):
            return html.DIV({}, "sidebar")

        NestedSidebar.scoped_style = {".nested-sidebar": {"color": "red"}}
        sidebar_mod.NestedSidebar = NestedSidebar
        sys.modules["nested_sidebar_mod"] = sidebar_mod

        layout_mod = types.ModuleType("nested_layout_mod")
        exec(
            "from webcompy.components import define_component\n"
            "from webcompy.elements import html\n"
            "from nested_sidebar_mod import NestedSidebar\n"
            "@define_component('nested-layout')\n"
            "def NestedLayout(context):\n"
            "    return html.DIV({}, NestedSidebar(None))\n",
            layout_mod.__dict__,
        )
        sys.modules["nested_layout_mod"] = layout_mod

        @define_component()
        def NestedPage(ctx):
            return html.DIV({}, "page")

        layout_lazy = lazy("nested_layout_mod:NestedLayout", __file__)
        router = Router(
            {"path": "/", "component": NestedPage},
            {
                "path": "/docs",
                "component": layout_lazy,
                "children": [{"path": "child", "component": NestedPage}],
            },
            mode="history",
        )
        app = WebComPyApp(
            root_component=lambda _: None,
            router=router,
            config=WebComPyAppConfig(base_url="/"),
        )

        assert layout_lazy._resolved is None

        first_request_seen_resolved = _run_generate(
            build_config,
            app,
            artifacts,
            check_first_request=lambda: layout_lazy._resolved is not None,
        )

        assert layout_lazy._resolved is layout_mod.NestedLayout
        assert first_request_seen_resolved is True

    def test_preload_disabled_router_still_preloads_nested_lazy_layout(self, tmp_path: Path) -> None:
        """SSG pre-resolution must not depend on the router's browser prefetch
        flag: a preload=False router with a nested lazy layout must still have
        the layout resolved before the first route is fetched, so style
        coverage is independent of generation order."""
        _pkg, build_config = _setup_app_pkg(tmp_path)
        artifacts = _make_artifacts(tmp_path)

        sidebar_mod = types.ModuleType("pd_sidebar_mod")

        @define_component()
        def PdSidebar(ctx):
            return html.DIV({}, "sidebar")

        PdSidebar.scoped_style = {".pd-sidebar": {"color": "red"}}
        sidebar_mod.PdSidebar = PdSidebar
        sys.modules["pd_sidebar_mod"] = sidebar_mod

        layout_mod = types.ModuleType("pd_layout_mod")
        exec(
            "from webcompy.components import define_component\n"
            "from webcompy.elements import html\n"
            "from pd_sidebar_mod import PdSidebar\n"
            "@define_component('pd-layout')\n"
            "def PdLayout(context):\n"
            "    return html.DIV({}, PdSidebar(None))\n",
            layout_mod.__dict__,
        )
        sys.modules["pd_layout_mod"] = layout_mod

        @define_component()
        def PdPage(ctx):
            return html.DIV({}, "page")

        layout_lazy = lazy("pd_layout_mod:PdLayout", __file__)
        router = Router(
            {"path": "/", "component": PdPage},
            {
                "path": "/docs",
                "component": layout_lazy,
                "children": [{"path": "child", "component": PdPage}],
            },
            mode="history",
            preload=False,
        )
        app = WebComPyApp(
            root_component=lambda _: None,
            router=router,
            config=WebComPyAppConfig(base_url="/"),
        )

        assert layout_lazy._resolved is None

        first_request_seen_resolved = _run_generate(
            build_config,
            app,
            artifacts,
            check_first_request=lambda: layout_lazy._resolved is not None,
        )

        assert layout_lazy._resolved is layout_mod.PdLayout
        assert first_request_seen_resolved is True
