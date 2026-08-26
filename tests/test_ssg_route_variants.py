from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import patch

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.components import define_component
from webcompy.elements import html
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
    def __init__(self, artifacts: BuildArtifacts, requested: list[str]) -> None:
        self.artifacts = artifacts
        self.requested = requested
        self.asgi = None
        self.hash_cache: list[str] = []


def _run_generate(
    build_config: WebComPyBuildConfig,
    app: WebComPyApp,
    artifacts: BuildArtifacts,
    requested: list[str],
) -> None:
    from webcompy_cli._generate import generate_static_site

    pkg = build_config.app_package_path
    saved_argv = sys.argv
    sys.argv = ["webcompy", "generate"]
    fake_mod = types.ModuleType("fake_app_mod")
    fake_mod.__file__ = str(pkg / "_app_mod.py")
    fake_mod.app = app
    sys.modules["fake_app_mod"] = fake_mod

    async def _recording_asgi(scope, receive, send):
        if scope["type"] != "http":
            return
        requested.append(scope["path"])
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/html")],
            }
        )
        await send({"type": "http.response.body", "body": b"<html></html>"})

    fake_serving = _FakeServingApp(artifacts, requested)
    fake_serving.asgi = _recording_asgi

    try:
        with (
            patch("webcompy_cli._generate.create_asgi_app", return_value=fake_serving),
            patch("webcompy_cli._generate.discover_config", return_value=build_config),
            patch("webcompy_cli._generate.get_static_files", return_value=()),
            patch("webcompy.ui._styles.get_styles_files", return_value={}, create=True),
        ):
            import asyncio

            asyncio.run(generate_static_site(app=app))
    finally:
        sys.modules.pop("fake_app_mod", None)
        sys.argv = saved_argv


class TestGenerateNestedRouteVariants:
    def test_nested_dynamic_parent_expands_into_ancestor_variants(self, tmp_path: Path) -> None:
        pkg, build_config = _setup_app_pkg(tmp_path)
        artifacts = _make_artifacts(tmp_path)
        requested: list[str] = []

        @define_component()
        def UserLayout(ctx):

            return html.DIV({})

        layout = UserLayout

        @define_component()
        def DocsPage(ctx):
            return html.DIV({})

        leaf = DocsPage
        router = Router(
            {
                "path": "/users/{uid}",
                "component": layout,
                "path_params": [{"uid": "alice"}, {"uid": "bob"}],
                "children": [{"path": "/docs", "component": leaf}],
            },
            mode="history",
            preload=False,
        )
        app = WebComPyApp(
            root_component=lambda _: None,
            router=router,
            config=WebComPyAppConfig(base_url="/"),
        )

        _run_generate(build_config, app, artifacts, requested)

        assert "/users/alice/docs" in requested
        assert "/users/bob/docs" in requested
        assert (pkg / "dist" / "users" / "alice" / "docs" / "index.html").exists()
        assert (pkg / "dist" / "users" / "bob" / "docs" / "index.html").exists()
        assert not (pkg / "dist" / "users" / "{uid}" / "docs" / "index.html").exists()

    def test_multiple_dynamic_levels_expand_cartesian_product(self, tmp_path: Path) -> None:
        _, build_config = _setup_app_pkg(tmp_path)
        artifacts = _make_artifacts(tmp_path)
        requested: list[str] = []

        @define_component()
        def UserLayout(ctx):

            return html.DIV({})

        layout = UserLayout

        @define_component()
        def DocPage(ctx):
            return html.DIV({})

        leaf = DocPage
        router = Router(
            {
                "path": "/users/{uid}",
                "component": layout,
                "path_params": [{"uid": "a"}, {"uid": "b"}],
                "children": [
                    {
                        "path": "/docs/{doc}",
                        "component": leaf,
                        "path_params": [{"doc": "x"}, {"doc": "y"}],
                    }
                ],
            },
            mode="history",
            preload=False,
        )
        app = WebComPyApp(
            root_component=lambda _: None,
            router=router,
            config=WebComPyAppConfig(base_url="/"),
        )

        _run_generate(build_config, app, artifacts, requested)

        assert "/users/a/docs/x" in requested
        assert "/users/a/docs/y" in requested
        assert "/users/b/docs/x" in requested
        assert "/users/b/docs/y" in requested

    def test_flat_route_with_path_params_keeps_previous_behavior(self, tmp_path: Path) -> None:
        pkg, build_config = _setup_app_pkg(tmp_path)
        artifacts = _make_artifacts(tmp_path)
        requested: list[str] = []

        @define_component()
        def UserPage(ctx):

            return html.DIV({})

        comp = UserPage
        router = Router(
            {"path": "/users/{uid}", "component": comp, "path_params": [{"uid": "alice"}]},
            mode="history",
            preload=False,
        )
        app = WebComPyApp(
            root_component=lambda _: None,
            router=router,
            config=WebComPyAppConfig(base_url="/"),
        )

        _run_generate(build_config, app, artifacts, requested)

        assert "/users/alice" in requested
        assert (pkg / "dist" / "users" / "alice" / "index.html").exists()
