from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import patch

from webcompy_cli._build import BuildArtifacts
from webcompy_cli.config._build_config import WebComPyBuildConfig


def _setup_app_pkg(tmp_path: Path, resources: dict[str, str]):
    pkg = tmp_path / "app"
    pkg.mkdir()
    for rel, content in resources.items():
        target = pkg / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    mod_path = pkg / "_app_mod.py"
    mod_path.write_text("app = None\n")
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ephemeral_app", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    build_config = WebComPyBuildConfig(app_module=mod)
    return pkg, build_config


class _FakeServingApp:
    def __init__(self, artifacts: BuildArtifacts) -> None:
        self.artifacts = artifacts
        self.asgi = None
        self.html_generator = None
        self.hash_cache: list[str] = []


def _run_generate(tmp_path: Path, artifacts: BuildArtifacts, build_config) -> None:
    from webcompy_cli._generate import generate_static_site

    pkg = build_config.app_package_path
    saved_argv = sys.argv
    sys.argv = ["webcompy", "generate"]
    fake_mod = types.ModuleType("fake_app_mod")
    fake_mod.__file__ = str(pkg / "_app_mod.py")
    sys.modules["fake_app_mod"] = fake_mod
    try:
        from webcompy.app._app import WebComPyApp
        from webcompy.app._config import WebComPyAppConfig

        app = WebComPyApp(
            root_component=lambda _: None,
            config=WebComPyAppConfig(base_url="/"),
        )
        fake_mod.app = app

        async def _trivial_asgi(scope, receive, send):
            if scope["type"] != "http":
                return
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


class TestSsgResourceCopy:
    def test_resources_copied_to_dist_under_webcompy_resource(self, tmp_path: Path) -> None:
        pkg, build_config = _setup_app_pkg(
            tmp_path,
            {
                "templates/card.html": "<p>hi</p>",
                "styles/main.css": "body{}",
                "icons/star.svg": "<svg/>",
            },
        )
        allow_list = frozenset(
            {
                "templates/card.html",
                "styles/main.css",
                "icons/star.svg",
            }
        )
        artifacts = BuildArtifacts(
            app_version="test-version",
            wheel_filename="test.whl",
            app_package_files={"test.whl": (b"x", "application/zip")},
            resource_allow_list=allow_list,
            dist_dir=tmp_path / "dist",
            dev_mode=False,
        )

        _run_generate(tmp_path, artifacts, build_config)

        dist = pkg / "dist"
        assert (dist / "_webcompy-resource" / "templates" / "card.html").exists()
        assert (dist / "_webcompy-resource" / "styles" / "main.css").read_text() == "body{}"
        assert (dist / "_webcompy-resource" / "icons" / "star.svg").read_text() == "<svg/>"

    def test_no_resource_copy_when_allow_list_is_none(self, tmp_path: Path) -> None:
        pkg, build_config = _setup_app_pkg(tmp_path, {"templates/card.html": "<p>hi</p>"})
        artifacts = BuildArtifacts(
            app_version="test-version",
            wheel_filename="test.whl",
            app_package_files={"test.whl": (b"x", "application/zip")},
            resource_allow_list=None,
            dist_dir=tmp_path / "dist",
            dev_mode=False,
        )

        _run_generate(tmp_path, artifacts, build_config)

        dist = pkg / "dist"
        assert not (dist / "_webcompy-resource").exists()
