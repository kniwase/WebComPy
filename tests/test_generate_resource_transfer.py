from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy.exception import WebComPyException
from webcompy_cli._build import BuildArtifacts
from webcompy_cli._generate import _collect_full_text_resources, generate_static_site
from webcompy_cli.config._build_config import WebComPyBuildConfig


def _make_build_config(tmp_path: Path, *, resource_transfer: str = "all-text") -> WebComPyBuildConfig:
    pkg = tmp_path / "app"
    pkg.mkdir()
    mod_path = pkg / "_app_mod.py"
    mod_path.write_text("app = None\n", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("_ephemeral_res_transfer", mod_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return WebComPyBuildConfig(app_module=mod, resource_transfer=resource_transfer)  # type: ignore[arg-type]


def _make_artifacts(allow_list: list[str]) -> BuildArtifacts:
    return BuildArtifacts(
        app_version="test-version",
        wheel_filename="test.whl",
        app_package_files={"test.whl": (b"x", "application/zip")},
        resource_allow_list=frozenset(allow_list),
    )


def _make_app() -> WebComPyApp:
    return WebComPyApp(root_component=lambda _: None, config=WebComPyAppConfig())


def test_invalid_resource_transfer_raises(tmp_path: Path) -> None:
    with pytest.raises(WebComPyException):
        _make_build_config(tmp_path, resource_transfer="bogus")


def test_default_mode_returns_none(tmp_path: Path) -> None:
    build_config = _make_build_config(tmp_path, resource_transfer="used")
    app = _make_app()
    assert _collect_full_text_resources(app, build_config, _make_artifacts(["documents/a.md"])) is None


def test_collect_full_text_resources_filters_binary(tmp_path: Path) -> None:
    build_config = _make_build_config(tmp_path)
    pkg = build_config.app_package_path
    (pkg / "documents").mkdir(parents=True)
    (pkg / "assets").mkdir(parents=True)
    (pkg / "documents" / "a.md").write_text("# A", encoding="utf-8")
    (pkg / "documents" / "b.json").write_text("{}", encoding="utf-8")
    (pkg / "assets" / "logo.png").write_bytes(b"\x89PNG\r\n")

    app = _make_app()
    full = _collect_full_text_resources(
        app,
        build_config,
        _make_artifacts(["documents/a.md", "documents/b.json", "assets/logo.png"]),
    )
    assert full == {"documents/a.md": b"# A", "documents/b.json": b"{}"}


class _FakeServingApp:
    def __init__(self, artifacts: BuildArtifacts) -> None:
        self.artifacts = artifacts
        self.asgi = None
        self.html_generator = None
        self.hash_cache: list[str] = []


def test_full_text_stash_cleared_after_generation(tmp_path: Path) -> None:
    build_config = _make_build_config(tmp_path, resource_transfer="all-text")
    pkg = build_config.app_package_path
    (pkg / "documents").mkdir(parents=True)
    (pkg / "documents" / "a.md").write_text("# A", encoding="utf-8")

    app = _make_app()
    build_config.app = app

    artifacts = _make_artifacts(["documents/a.md"])
    serving = _FakeServingApp(artifacts)
    stash_seen_during_generation: list[bool] = []

    async def _trivial_asgi(scope, receive, send):
        if scope["type"] != "http":
            return
        stash_seen_during_generation.append(app._ssg_full_text_resources is not None)
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/html")],
            }
        )
        await send({"type": "http.response.body", "body": b"<html></html>"})

    serving.asgi = _trivial_asgi

    saved_argv = sys.argv
    sys.argv = ["webcompy", "generate"]
    try:
        with (
            patch("webcompy_cli._generate.create_asgi_app", return_value=serving),
            patch("webcompy_cli._generate.discover_config", return_value=build_config),
            patch("webcompy_cli._generate.get_static_files", return_value=()),
            patch("webcompy.ui._styles.get_styles_files", return_value={}, create=True),
        ):
            asyncio.run(generate_static_site())
    finally:
        sys.argv = saved_argv

    assert stash_seen_during_generation and all(stash_seen_during_generation), (
        "the full-text stash must be populated while routes are generated"
    )
    assert app._ssg_full_text_resources is None, (
        "the stash must be cleared after generation so dev/prod serving stays per-context ('used')"
    )
