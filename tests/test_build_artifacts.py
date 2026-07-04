from __future__ import annotations

import pathlib
from unittest.mock import MagicMock, patch

from webcompy.app._app import WebComPyApp
from webcompy.components._generator import define_component
from webcompy_cli._build import BuildArtifacts
from webcompy_cli._utils import generate_app_version
from webcompy_cli.config._build_config import WebComPyBuildConfig
from webcompy_cli.config._server_config import WebComPyServerConfig
from webcompy_server import configure_server_context


class TestBuildArtifactsDataclass:
    def test_minimal_instantiation(self):
        artifacts = BuildArtifacts(
            app_version="25.100.1",
            wheel_filename="my_app-1.0-py3-none-any.whl",
        )
        assert artifacts.app_version == "25.100.1"
        assert artifacts.wheel_filename == "my_app-1.0-py3-none-any.whl"
        assert artifacts.extra_wheel_filenames is None
        assert artifacts.pyodide_package_names == []
        assert artifacts.wasm_local_urls is None
        assert artifacts.lockfile_url is None
        assert artifacts.runtime_serving == "cdn"
        assert artifacts.app_package_files is None
        assert artifacts.wasm_asset_files is None
        assert artifacts.runtime_asset_files is None
        assert artifacts.dist_dir is None
        assert artifacts.dev_mode is False

    def test_full_instantiation(self):
        artifacts = BuildArtifacts(
            app_version="25.100.1",
            wheel_filename="app-1.0.whl",
            fw_wheel_filename="webcompy-1.0.whl",
            extra_wheel_filenames=["dep-1.0.whl"],
            pyodide_package_names=["numpy"],
            wasm_local_urls={"numpy": "/_webcompy-assets/packages/numpy.whl"},
            lockfile_url="https://cdn/pyodide-lock.json",
            runtime_serving="local",
            app_package_files={"app.whl": (b"content", "application/zip")},
            wasm_asset_files={"numpy.whl": "/tmp/numpy.whl"},
            runtime_asset_files={"core.js": "/tmp/core.js"},
            dist_dir="/dist",
            dev_mode=True,
        )
        assert artifacts.app_version == "25.100.1"
        assert artifacts.fw_wheel_filename == "webcompy-1.0.whl"
        assert artifacts.extra_wheel_filenames == ["dep-1.0.whl"]
        assert artifacts.pyodide_package_names == ["numpy"]
        assert artifacts.wasm_local_urls == {"numpy": "/_webcompy-assets/packages/numpy.whl"}
        assert artifacts.app_package_files == {"app.whl": (b"content", "application/zip")}
        assert artifacts.dev_mode is True


class TestCreateAsgiAppMode:
    def _make_minimal_app(self) -> WebComPyApp:
        @define_component
        def _Root(context):
            from webcompy.elements import html

            return html.DIV({}, "hello")

        app = WebComPyApp(root_component=_Root)
        configure_server_context(app)
        return app

    def _make_fake_build_config(self) -> MagicMock:
        server_config = WebComPyServerConfig(dev=True)
        build_config = MagicMock(spec=WebComPyBuildConfig)
        build_config.server = server_config
        build_config.wasm_serving = None
        build_config.runtime_serving = None
        build_config.standalone = False
        build_config.serve_all_deps = False
        build_config.wheel_mode = "bundled"
        build_config.app_package_path = pathlib.Path("/tmp/test_app")
        build_config.static_files_dir = "static"
        return build_config

    def test_prod_mode_excludes_sse_route(self):
        app = self._make_minimal_app()
        build_config = self._make_fake_build_config()
        artifacts = BuildArtifacts(
            app_version="test-version",
            wheel_filename="test.whl",
            app_package_files={"test.whl": (b"content", "application/zip")},
        )

        with (
            patch("webcompy_cli._server.resolve_build_artifacts", return_value=artifacts),
            patch("webcompy_cli._server.get_static_files", return_value=()),
        ):
            from webcompy_cli._server import create_asgi_app

            serving = create_asgi_app(app, build_config, mode="prod")

        route_paths = [r.path for r in serving.asgi.routes]
        assert "/_webcompy_reload" not in route_paths, "SSE route should be excluded in prod mode"

    def test_prod_mode_sets_dev_false(self):
        app = self._make_minimal_app()
        build_config = self._make_fake_build_config()
        artifacts = BuildArtifacts(
            app_version="test-version",
            wheel_filename="test.whl",
            app_package_files={"test.whl": (b"content", "application/zip")},
        )

        with (
            patch("webcompy_cli._server.resolve_build_artifacts", return_value=artifacts),
            patch("webcompy_cli._server.get_static_files", return_value=()),
        ):
            from webcompy_cli._server import create_asgi_app

            create_asgi_app(app, build_config, mode="prod")

        assert build_config.server.dev is False, "prod mode should set server.dev=False"

    def test_dev_mode_includes_sse_route(self):
        app = self._make_minimal_app()
        build_config = self._make_fake_build_config()
        artifacts = BuildArtifacts(
            app_version="test-version",
            wheel_filename="test.whl",
            app_package_files={"test.whl": (b"content", "application/zip")},
        )

        with (
            patch("webcompy_cli._server.resolve_build_artifacts", return_value=artifacts),
            patch("webcompy_cli._server.get_static_files", return_value=()),
        ):
            from webcompy_cli._server import create_asgi_app

            serving = create_asgi_app(app, build_config, mode="dev")

        route_paths = [r.path for r in serving.asgi.routes]
        assert "/_webcompy_reload" in route_paths, "SSE route should be included in dev mode"

    def test_dev_mode_sets_dev_true(self):
        app = self._make_minimal_app()
        build_config = self._make_fake_build_config()
        build_config.server.dev = False  # start with False
        artifacts = BuildArtifacts(
            app_version="test-version",
            wheel_filename="test.whl",
            app_package_files={"test.whl": (b"content", "application/zip")},
        )

        with (
            patch("webcompy_cli._server.resolve_build_artifacts", return_value=artifacts),
            patch("webcompy_cli._server.get_static_files", return_value=()),
        ):
            from webcompy_cli._server import create_asgi_app

            create_asgi_app(app, build_config, mode="dev")

        assert build_config.server.dev is True, "dev mode should set server.dev=True"

    def test_default_mode_is_prod(self):
        app = self._make_minimal_app()
        build_config = self._make_fake_build_config()
        artifacts = BuildArtifacts(
            app_version="test-version",
            wheel_filename="test.whl",
            app_package_files={"test.whl": (b"content", "application/zip")},
        )

        with (
            patch("webcompy_cli._server.resolve_build_artifacts", return_value=artifacts),
            patch("webcompy_cli._server.get_static_files", return_value=()),
        ):
            from webcompy_cli._server import create_asgi_app

            serving = create_asgi_app(app, build_config)

        route_paths = [r.path for r in serving.asgi.routes]
        assert "/_webcompy_reload" not in route_paths, "default mode should exclude SSE (prod)"


class TestGenerateAppVersion:
    def test_returns_zero_version_when_none(self):
        assert generate_app_version() == "0.0.0"
        assert generate_app_version(None) == "0.0.0"

    def test_returns_explicit_version(self):
        assert generate_app_version("1.2.3") == "1.2.3"
        assert generate_app_version("25.100.1") == "25.100.1"
