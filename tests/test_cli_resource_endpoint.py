from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from webcompy_cli._build import BuildArtifacts
from webcompy_cli.config._build_config import WebComPyBuildConfig


def _make_app_pkg(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create an "app" package at ``tmp_path / app`` with the given files
    (POSIX-relative) and return the package path.
    """
    pkg = tmp_path / "app"
    pkg.mkdir()
    for rel, content in files.items():
        target = pkg / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return pkg


def _make_minimal_app_module(pkg_dir: Path, name: str = "app_mod.py") -> object:
    """Create a Python module file at ``pkg_dir / name`` exposing a
    top-level ``app`` attribute, so that
    ``WebComPyBuildConfig(app_module=mod).app_package_path == pkg_dir``.
    """
    mod_path = pkg_dir / name
    mod_path.write_text("app = None\n")
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ephemeral_app", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _setup_app_in_pkg(tmp_path: Path, resources: dict[str, str]):
    pkg = _make_app_pkg(tmp_path, resources)
    app_module = _make_minimal_app_module(pkg)
    build_config = WebComPyBuildConfig(app_module=app_module)
    return pkg, app_module, build_config


class TestResourceEndpoint:
    def _setup(
        self,
        tmp_path: Path,
        resources: dict[str, str],
        allow_list: frozenset[str] | None = None,
    ):
        pkg, _app_module, build_config = _setup_app_in_pkg(tmp_path, resources)
        if allow_list is None:
            allow_list = frozenset(resources.keys())

        artifacts = BuildArtifacts(
            app_version="test-version",
            wheel_filename="test.whl",
            app_package_files={"test.whl": (b"x", "application/zip")},
            resource_allow_list=allow_list,
        )

        from webcompy.app._app import WebComPyApp
        from webcompy.app._config import WebComPyAppConfig

        app = WebComPyApp(
            root_component=lambda _: None,
            config=WebComPyAppConfig(base_url="/"),
        )

        return app, build_config, artifacts, pkg

    @pytest.mark.asyncio
    async def test_allowlisted_file_served_with_correct_content_type(self, tmp_path: Path) -> None:
        app, build_config, artifacts, _ = self._setup(
            tmp_path,
            {
                "templates/card.html": "<p>hi</p>",
                "styles/main.css": "body{color:red}",
            },
        )

        with (
            patch(
                "webcompy_cli._server.resolve_build_artifacts",
                return_value=artifacts,
            ),
            patch("webcompy_cli._server.get_static_files", return_value=()),
        ):
            from webcompy_cli._server import create_asgi_app

            serving = create_asgi_app(app, build_config, mode="prod")
            transport = httpx.ASGITransport(app=serving.asgi)

            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/_webcompy-resource/templates/card.html")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert response.text == "<p>hi</p>"

    @pytest.mark.asyncio
    async def test_non_allowlisted_returns_404(self, tmp_path: Path) -> None:
        # File exists on disk but is NOT in the allow-list
        app, build_config, artifacts, _ = self._setup(
            tmp_path,
            {
                "templates/card.html": "<p>hi</p>",
                "internal/secret.txt": "shh",
            },
            allow_list=frozenset({"templates/card.html"}),
        )

        with (
            patch(
                "webcompy_cli._server.resolve_build_artifacts",
                return_value=artifacts,
            ),
            patch("webcompy_cli._server.get_static_files", return_value=()),
        ):
            from webcompy_cli._server import create_asgi_app

            serving = create_asgi_app(app, build_config, mode="prod")
            transport = httpx.ASGITransport(app=serving.asgi)

            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/_webcompy-resource/internal/secret.txt")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_traversal_returns_403(self, tmp_path: Path) -> None:
        """An attacker-controlled path that escapes the package root returns
        a 403 from the containment check, not the file content.
        """
        app, build_config, artifacts, _ = self._setup(
            tmp_path,
            {"a.html": "x"},
        )

        with (
            patch(
                "webcompy_cli._server.resolve_build_artifacts",
                return_value=artifacts,
            ),
            patch("webcompy_cli._server.get_static_files", return_value=()),
        ):
            from webcompy_cli._server import create_asgi_app

            serving = create_asgi_app(app, build_config, mode="prod")
            transport = httpx.ASGITransport(app=serving.asgi)

            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/_webcompy-resource/../pyproject.toml")

        assert response.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_symlink_escape_returns_403(self, tmp_path: Path) -> None:
        pkg, _app_module, build_config = _setup_app_in_pkg(tmp_path, {"a.html": "x"})
        # Symlink inside the package pointing outside the root
        (pkg / "escape_link").symlink_to("/etc/passwd")
        artifacts = BuildArtifacts(
            app_version="test-version",
            wheel_filename="test.whl",
            app_package_files={"test.whl": (b"x", "application/zip")},
            resource_allow_list=frozenset({"a.html", "escape_link"}),
        )

        from webcompy.app._app import WebComPyApp
        from webcompy.app._config import WebComPyAppConfig

        app = WebComPyApp(
            root_component=lambda _: None,
            config=WebComPyAppConfig(base_url="/"),
        )

        with (
            patch(
                "webcompy_cli._server.resolve_build_artifacts",
                return_value=artifacts,
            ),
            patch("webcompy_cli._server.get_static_files", return_value=()),
        ):
            from webcompy_cli._server import create_asgi_app

            serving = create_asgi_app(app, build_config, mode="prod")
            transport = httpx.ASGITransport(app=serving.asgi)

            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/_webcompy-resource/escape_link")

        assert response.status_code == 403


class TestResourceEndpointDisabled:
    @pytest.mark.asyncio
    async def test_no_endpoint_when_resource_allow_list_is_none(self, tmp_path: Path) -> None:
        """When the build produces no resource allow-list (e.g., user disabled
        auto-detection with resources=[]), the resource route is not
        registered and requests 404.
        """
        from webcompy.app._app import WebComPyApp
        from webcompy.app._config import WebComPyAppConfig

        _pkg, _, _ = _setup_app_in_pkg(tmp_path, {"templates/card.html": "<p>hi</p>"})
        # Use a dummy module elsewhere so app_package_path resolves cleanly.
        dummy = tmp_path / "_unused_app_mod.py"
        dummy.write_text("app = None\n")
        app_module = (
            _make_minimal_app_module.__wrapped__(dummy.parent, dummy.name)
            if hasattr(_make_minimal_app_module, "__wrapped__")
            else None
        )
        import importlib.util

        spec = importlib.util.spec_from_file_location("_ephemeral_app_dummy", dummy)
        app_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_module)
        build_config = WebComPyBuildConfig(app_module=app_module)
        artifacts = BuildArtifacts(
            app_version="test-version",
            wheel_filename="test.whl",
            app_package_files={"test.whl": (b"x", "application/zip")},
            resource_allow_list=None,
        )

        app = WebComPyApp(
            root_component=lambda _: None,
            config=WebComPyAppConfig(base_url="/"),
        )

        with (
            patch(
                "webcompy_cli._server.resolve_build_artifacts",
                return_value=artifacts,
            ),
            patch("webcompy_cli._server.get_static_files", return_value=()),
        ):
            from webcompy_cli._server import create_asgi_app

            serving = create_asgi_app(app, build_config, mode="prod")
            transport = httpx.ASGITransport(app=serving.asgi)

            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/_webcompy-resource/templates/card.html")

        assert response.status_code == 404
