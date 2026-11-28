from __future__ import annotations

import importlib.util
import json
import logging
import os
import pathlib
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from webcompy.app._app import WebComPyApp
from webcompy.app._config import WebComPyAppConfig
from webcompy.components._generator import define_component
from webcompy.elements import html
from webcompy.exception import WebComPyException
from webcompy.router import Router
from webcompy_cli._server import (
    _DEV_SERVER_ARGS_ENV,
    _create_dev_asgi_app,
    _ServingApp,
    run_server,
)
from webcompy_cli.config._build_config import WebComPyBuildConfig
from webcompy_cli.config._server_config import WebComPyServerConfig


def _make_config(
    tmp_path: pathlib.Path,
    *,
    dev: bool = False,
    port: int = 8080,
    router_mode: str = "history",
) -> tuple[WebComPyApp, WebComPyBuildConfig, pathlib.Path]:
    pkg = tmp_path / "demo_pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")

    @define_component()
    def ReloadTestRoot(_):
        return html.DIV({}, "ok")

    router = Router({"path": "/", "component": ReloadTestRoot}, mode=router_mode)  # type: ignore[arg-type]
    app = WebComPyApp(
        root_component=ReloadTestRoot,
        router=router,
        config=WebComPyAppConfig(base_url="/"),
    )
    mod_path = pkg / "app.py"
    mod_path.write_text("app = None\n", encoding="utf-8")
    mod = types.ModuleType("demo_pkg.app")
    mod.__file__ = str(mod_path)
    mod.app = app  # type: ignore[attr-defined]
    build_config = WebComPyBuildConfig(
        app_module=mod,
        dependencies=[],
        server=WebComPyServerConfig(port=port, dev=dev),
    )
    return app, build_config, pkg


class TestRunServerReloadDispatch:
    def test_cli_dev_flag_launches_uvicorn_factory_reload(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, build_config, pkg = _make_config(tmp_path, dev=False, port=9001)
        captured: dict[str, object] = {}

        def fake_uvicorn_run(app_target, **kwargs):
            captured["target"] = app_target
            captured["kwargs"] = kwargs
            captured["env"] = os.environ.get(_DEV_SERVER_ARGS_ENV)

        cli_args = {
            "dev": True,
            "port": 9002,
            "config": "demo_pkg.webcompy_config",
            "serve_all_deps": False,
            "wasm_serving": "local",
            "runtime_serving": "local",
            "standalone": False,
            "wheel_mode": "split",
        }
        monkeypatch.delenv(_DEV_SERVER_ARGS_ENV, raising=False)
        with (
            patch("webcompy_cli._server.get_params", return_value=("start", cli_args)),
            patch("webcompy_cli._server.discover_config", return_value=build_config),
            patch("webcompy_cli._server.create_asgi_app") as mock_create,
            patch("webcompy_cli._server.uvicorn.run", side_effect=fake_uvicorn_run),
        ):
            run_server()

        mock_create.assert_not_called()
        assert captured["target"] == "webcompy_cli._server:_create_dev_asgi_app"
        assert captured["kwargs"] == {
            "host": "0.0.0.0",
            "port": 9002,
            "reload": True,
            "reload_dirs": [str(pkg)],
            "app_dir": os.getcwd(),
            "factory": True,
        }
        assert isinstance(captured["env"], str)
        payload = json.loads(captured["env"])
        assert payload == {
            "config": "demo_pkg.webcompy_config",
            "app_module": None,
            "serve_all_deps": False,
            "wasm_serving": "local",
            "runtime_serving": "local",
            "standalone": False,
            "wheel_mode": "split",
        }
        assert _DEV_SERVER_ARGS_ENV not in os.environ

    def test_server_config_dev_true_without_cli_flag_uses_reload(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, build_config, pkg = _make_config(tmp_path, dev=True, port=8085)
        captured: dict[str, object] = {}

        def fake_uvicorn_run(app_target, **kwargs):
            captured["target"] = app_target
            captured["kwargs"] = kwargs

        monkeypatch.setenv(_DEV_SERVER_ARGS_ENV, "previous-value")
        with (
            patch("webcompy_cli._server.get_params", return_value=("start", {"dev": False, "config": "cfg"})),
            patch("webcompy_cli._server.discover_config", return_value=build_config),
            patch("webcompy_cli._server.create_asgi_app") as mock_create,
            patch("webcompy_cli._server.uvicorn.run", side_effect=fake_uvicorn_run),
        ):
            run_server()

        mock_create.assert_not_called()
        assert captured["target"] == "webcompy_cli._server:_create_dev_asgi_app"
        assert captured["kwargs"] == {
            "host": "0.0.0.0",
            "port": 8085,
            "reload": True,
            "reload_dirs": [str(pkg)],
            "app_dir": os.getcwd(),
            "factory": True,
        }
        assert os.environ.get(_DEV_SERVER_ARGS_ENV) == "previous-value"

    def test_prod_mode_runs_asgi_instance_directly(self, tmp_path: pathlib.Path) -> None:
        _, build_config, _ = _make_config(tmp_path, dev=False, port=8080)
        fake_asgi = MagicMock()
        fake_serving = _ServingApp(
            asgi=fake_asgi,
            html_generator=MagicMock(),
            hash_cache=[],
            artifacts=MagicMock(),
        )
        captured: dict[str, object] = {}

        def fake_uvicorn_run(app_target, **kwargs):
            captured["target"] = app_target
            captured["kwargs"] = kwargs

        with (
            patch("webcompy_cli._server.get_params", return_value=("start", {"dev": False})),
            patch("webcompy_cli._server.discover_config", return_value=build_config),
            patch("webcompy_cli._server.create_asgi_app", return_value=fake_serving) as mock_create,
            patch("webcompy_cli._server.uvicorn.run", side_effect=fake_uvicorn_run),
        ):
            run_server()

        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs["mode"] == "prod"
        assert captured["target"] is fake_asgi
        assert captured["kwargs"] == {"host": "0.0.0.0", "port": 8080, "reload": False}

    def test_importable_direct_app_with_dev_uses_factory_reload(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pkg = tmp_path / "direct_pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        mod_file = pkg / "direct_app.py"
        mod_file.write_text("app = None\n", encoding="utf-8")

        @define_component()
        def DirectRoot(_):
            return html.DIV({}, "direct")

        app = WebComPyApp(
            root_component=DirectRoot,
            router=Router({"path": "/", "component": DirectRoot}, mode="history"),
        )
        spec = importlib.util.spec_from_file_location("direct_pkg.direct_app", mod_file)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(mod_file)
        mod.app = app  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "direct_pkg.direct_app", mod)

        captured: dict[str, object] = {}

        def fake_uvicorn_run(app_target, **kwargs):
            captured["target"] = app_target
            captured["kwargs"] = kwargs
            captured["env"] = os.environ.get(_DEV_SERVER_ARGS_ENV)

        with (
            patch("webcompy_cli._server.get_params", return_value=("start", {"dev": True, "port": 8123})),
            patch("webcompy_cli._server.create_asgi_app") as mock_create,
            patch("webcompy_cli._server.uvicorn.run", side_effect=fake_uvicorn_run),
        ):
            run_server(app)

        mock_create.assert_not_called()
        assert captured["target"] == "webcompy_cli._server:_create_dev_asgi_app"
        assert isinstance(captured["env"], str)
        payload = json.loads(captured["env"])
        assert payload["config"] is None
        assert payload["app_module"] == "direct_pkg.direct_app"
        assert captured["kwargs"] == {
            "host": "0.0.0.0",
            "port": 8123,
            "reload": True,
            "reload_dirs": [str(pkg)],
            "app_dir": os.getcwd(),
            "factory": True,
        }

    def test_anonymous_in_memory_app_with_dev_falls_back_to_no_reload_with_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        @define_component()
        def EphemeralRoot(_):
            return html.DIV({}, "ephemeral")

        app = WebComPyApp(
            root_component=EphemeralRoot,
            router=Router({"path": "/", "component": EphemeralRoot}, mode="history"),
        )
        fake_asgi = MagicMock()
        fake_serving = _ServingApp(
            asgi=fake_asgi,
            html_generator=MagicMock(),
            hash_cache=[],
            artifacts=MagicMock(),
        )
        captured: dict[str, object] = {}

        def fake_uvicorn_run(app_target, **kwargs):
            captured["target"] = app_target
            captured["kwargs"] = kwargs

        with (
            caplog.at_level(logging.WARNING, logger="webcompy_cli._server"),
            patch("webcompy_cli._server.get_params", return_value=("start", {"dev": True, "port": 8124})),
            patch("webcompy_cli._server.create_asgi_app", return_value=fake_serving) as mock_create,
            patch("webcompy_cli._server.uvicorn.run", side_effect=fake_uvicorn_run),
        ):
            run_server(app)

        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs["mode"] == "dev"
        assert captured["target"] is fake_asgi
        assert captured["kwargs"] == {"host": "0.0.0.0", "port": 8124, "reload": False}
        assert "reload=False" in caplog.text


class TestCreateDevAsgiAppFactory:
    def test_raises_when_env_var_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(_DEV_SERVER_ARGS_ENV, raising=False)
        with pytest.raises(WebComPyException, match=_DEV_SERVER_ARGS_ENV):
            _create_dev_asgi_app()

    def test_discovers_config_and_applies_cli_overrides(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app, build_config, _ = _make_config(tmp_path, dev=False)
        fake_asgi = MagicMock()
        fake_serving = _ServingApp(
            asgi=fake_asgi,
            html_generator=MagicMock(),
            hash_cache=[],
            artifacts=MagicMock(),
        )
        monkeypatch.setenv(
            _DEV_SERVER_ARGS_ENV,
            json.dumps(
                {
                    "config": "demo_pkg.webcompy_config",
                    "app_module": None,
                    "serve_all_deps": False,
                    "wasm_serving": "local",
                    "runtime_serving": "local",
                    "standalone": True,
                    "wheel_mode": "split",
                }
            ),
        )

        with (
            patch("webcompy_cli._server.discover_config", return_value=build_config) as mock_discover,
            patch("webcompy_cli._server.create_asgi_app", return_value=fake_serving) as mock_create,
        ):
            result = _create_dev_asgi_app()

        mock_discover.assert_called_once_with("demo_pkg.webcompy_config")
        mock_create.assert_called_once_with(app, build_config, mode="dev")
        assert build_config.standalone is True
        assert build_config.serve_all_deps is True
        assert build_config.wasm_serving == "local"
        assert build_config.runtime_serving == "local"
        assert build_config.wheel_mode == "split"
        assert result is fake_asgi

    def test_imports_app_module_when_set(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        pkg = tmp_path / "mod_pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        app_file = pkg / "my_app.py"
        app_file.write_text(
            "from webcompy.app import WebComPyApp\n"
            "from webcompy.components import define_component\n"
            "from webcompy.elements import html\n"
            "from webcompy.router import Router\n"
            "@define_component()\n"
            "def ModTestRoot(_):\n"
            "    return html.DIV({}, 'from-mod')\n"
            "app = WebComPyApp(root_component=ModTestRoot, router=Router({'path': '/', 'component': ModTestRoot}, mode='history'))\n",
            encoding="utf-8",
        )
        monkeypatch.syspath_prepend(str(tmp_path))
        monkeypatch.setenv(
            _DEV_SERVER_ARGS_ENV,
            json.dumps({"config": None, "app_module": "mod_pkg.my_app"}),
        )
        fake_asgi = MagicMock()
        fake_serving = _ServingApp(
            asgi=fake_asgi,
            html_generator=MagicMock(),
            hash_cache=[],
            artifacts=MagicMock(),
        )
        try:
            with patch("webcompy_cli._server.create_asgi_app", return_value=fake_serving) as mock_create:
                result = _create_dev_asgi_app()

            assert result is fake_asgi
            mock_create.assert_called_once()
            passed_app, passed_config = mock_create.call_args.args
            assert passed_app is sys.modules["mod_pkg.my_app"].app
            assert passed_config.app_package_path == pkg
            assert mock_create.call_args.kwargs == {"mode": "dev"}
        finally:
            sys.modules.pop("mod_pkg.my_app", None)
            sys.modules.pop("mod_pkg", None)
