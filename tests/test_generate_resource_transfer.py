from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy.exception import WebComPyException
from webcompy_cli._build import BuildArtifacts
from webcompy_cli._generate import _collect_full_text_resources
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
