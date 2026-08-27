from pathlib import Path

import pytest

from webcompy.app._config import WebComPyAppConfig
from webcompy_cli.config._build_config import WebComPyBuildConfig
from webcompy_cli.config._server_config import LockfileSyncConfig, WebComPyServerConfig


class TestWebComPyAppConfig:
    def test_defaults(self):
        config = WebComPyAppConfig()
        assert config.base_url == "/"
        assert config.selector == "#webcompy-app"
        assert config.profile is False
        assert config.hydrate is True
        assert config.scroll_restoration is True
        assert config.scripts == []
        assert config.plugins == []
        assert config.compression_threshold == 1024

    def test_base_url_normalization_trailing_slash(self):
        config = WebComPyAppConfig(base_url="app")
        assert config.base_url == "/app/"

    def test_base_url_normalization_leading_slash(self):
        config = WebComPyAppConfig(base_url="/app")
        assert config.base_url == "/app/"

    def test_base_url_normalization_both_slashes(self):
        config = WebComPyAppConfig(base_url="/app/")
        assert config.base_url == "/app/"

    def test_base_url_normalization_empty(self):
        config = WebComPyAppConfig(base_url="")
        assert config.base_url == "/"

    def test_base_url_normalization_root(self):
        config = WebComPyAppConfig(base_url="/")
        assert config.base_url == "/"

    def test_selector_default(self):
        config = WebComPyAppConfig()
        assert config.selector == "#webcompy-app"

    def test_custom_selector(self):
        config = WebComPyAppConfig(selector="#custom")
        assert config.selector == "#custom"

    def test_profile_default(self):
        config = WebComPyAppConfig()
        assert config.profile is False

    def test_profile_enabled(self):
        config = WebComPyAppConfig(profile=True)
        assert config.profile is True

    def test_hydrate_default(self):
        config = WebComPyAppConfig()
        assert config.hydrate is True

    def test_hydrate_disabled(self):
        config = WebComPyAppConfig(hydrate=False)
        assert config.hydrate is False

    def test_scroll_restoration_default(self):
        config = WebComPyAppConfig()
        assert config.scroll_restoration is True

    def test_scroll_restoration_disabled(self):
        config = WebComPyAppConfig(scroll_restoration=False)
        assert config.scroll_restoration is False

    def test_theme_default_is_none(self):
        config = WebComPyAppConfig()
        assert config.theme is None

    def test_compression_threshold_default(self):
        config = WebComPyAppConfig()
        assert config.compression_threshold == 1024

    def test_compression_threshold_none(self):
        config = WebComPyAppConfig(compression_threshold=None)
        assert config.compression_threshold is None

    def test_compression_threshold_zero(self):
        config = WebComPyAppConfig(compression_threshold=0)
        assert config.compression_threshold == 0

    def test_compression_threshold_custom(self):
        config = WebComPyAppConfig(compression_threshold=4096)
        assert config.compression_threshold == 4096

    def test_theme_default_only_uses_system(self):
        config = WebComPyAppConfig(theme={"default": "dark"})
        assert config.theme == {"default": "dark", "persist": True}

    def test_theme_persist_false(self):
        config = WebComPyAppConfig(theme={"default": "light", "persist": False})
        assert config.theme == {"default": "light", "persist": False}

    def test_theme_default_system_when_omitted(self):
        config = WebComPyAppConfig(theme={"persist": False})
        assert config.theme == {"default": "system", "persist": False}

    def test_theme_invalid_default_raises(self):
        import pytest

        with pytest.raises(ValueError, match="theme\\['default'\\]"):
            WebComPyAppConfig(theme={"default": "purple"})

    def test_theme_invalid_persist_raises(self):
        import pytest

        with pytest.raises(TypeError, match="theme\\['persist'\\]"):
            WebComPyAppConfig(theme={"persist": "yes"})

    def test_theme_must_be_dict(self):
        import pytest

        with pytest.raises(TypeError, match="theme must be a dict"):
            WebComPyAppConfig(theme="not a dict")

    def test_loading_default_is_none(self):
        config = WebComPyAppConfig()
        assert config.loading is None

    def test_loading_defaults_normalized(self):
        config = WebComPyAppConfig(loading={})
        assert config.loading == {
            "mode": "auto",
            "interaction": "block",
            "stages": True,
            "dormant": True,
            "messages": {},
            "template": None,
            "reveal_delay_ms": 350,
            "fade_out_ms": 250,
            "timeout_seconds": 30,
        }

    def test_loading_partial_config_keeps_defaults(self):
        config = WebComPyAppConfig(loading={"mode": "content", "interaction": "passthrough"})
        assert config.loading["mode"] == "content"
        assert config.loading["interaction"] == "passthrough"
        assert config.loading["stages"] is True
        assert config.loading["reveal_delay_ms"] == 350

    def test_loading_dormant_false(self):
        config = WebComPyAppConfig(loading={"dormant": False})
        assert config.loading["dormant"] is False

    def test_loading_messages_kept(self):
        config = WebComPyAppConfig(loading={"messages": {"runtime_download": "下載中…"}})
        assert config.loading["messages"] == {"runtime_download": "下載中…"}

    def test_loading_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="mode"):
            WebComPyAppConfig(loading={"mode": "fancy"})

    def test_loading_invalid_interaction_raises(self):
        with pytest.raises(ValueError, match="interaction"):
            WebComPyAppConfig(loading={"interaction": "let-go"})

    def test_loading_unknown_key_raises(self):
        with pytest.raises(ValueError, match="unknown keys"):
            WebComPyAppConfig(loading={"spinner": True})

    def test_loading_invalid_fade_type_raises(self):
        with pytest.raises(TypeError, match="fade_out_ms"):
            WebComPyAppConfig(loading={"fade_out_ms": "250"})

    def test_loading_negative_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout_seconds"):
            WebComPyAppConfig(loading={"timeout_seconds": -1})

    def test_loading_reveal_delay_above_max_raises(self):
        with pytest.raises(ValueError, match="reveal_delay_ms"):
            WebComPyAppConfig(loading={"reveal_delay_ms": 10001})

    def test_loading_fade_out_above_max_raises(self):
        with pytest.raises(ValueError, match="fade_out_ms"):
            WebComPyAppConfig(loading={"fade_out_ms": 10001})

    def test_loading_timeout_above_max_raises(self):
        with pytest.raises(ValueError, match="timeout_seconds"):
            WebComPyAppConfig(loading={"timeout_seconds": 3601})

    def test_loading_int_max_values_accepted(self):
        config = WebComPyAppConfig(loading={"reveal_delay_ms": 10000, "fade_out_ms": 10000, "timeout_seconds": 3600})
        assert config.loading["reveal_delay_ms"] == 10000
        assert config.loading["fade_out_ms"] == 10000
        assert config.loading["timeout_seconds"] == 3600

    def test_loading_bool_rejected_for_int_keys(self):
        with pytest.raises(TypeError, match="reveal_delay_ms"):
            WebComPyAppConfig(loading={"reveal_delay_ms": True})

    def test_loading_invalid_dormant_type_raises(self):
        with pytest.raises(TypeError, match="dormant"):
            WebComPyAppConfig(loading={"dormant": "yes"})

    def test_loading_unknown_stage_key_raises(self):
        with pytest.raises(ValueError, match="stage keys"):
            WebComPyAppConfig(loading={"messages": {"init": "Starting…"}})

    def test_loading_message_value_must_be_str(self):
        with pytest.raises(TypeError, match="messages"):
            WebComPyAppConfig(loading={"messages": {"runtime_download": 123}})

    def test_loading_messages_default_not_shared(self):
        config_a = WebComPyAppConfig(loading={})
        config_b = WebComPyAppConfig(loading={})
        config_a.loading["messages"]["runtime_download"] = "Mutated"
        assert config_b.loading["messages"] == {}

    def test_loading_must_be_dict(self):
        with pytest.raises(TypeError, match="loading must be a dict"):
            WebComPyAppConfig(loading="overlay")


class TestWebComPyBuildConfig:
    def _make_module(self, tmp_path, code="app = None"):
        app_module = tmp_path / "app_mod.py"
        app_module.write_text(code)
        import sys

        sys.path.insert(0, str(tmp_path))
        try:
            import importlib

            return importlib.import_module("app_mod")
        finally:
            sys.path.pop(0)

    def _full_app_code(self):
        return (
            "from webcompy.app import WebComPyApp\n"
            "from webcompy.components._generator import define_component\n"
            "from webcompy.elements import html\n\n"
            "@define_component()\n"
            "def AppRoot(context):\n"
            "    return html.DIV({}, 'test')\n\n"
            "app = WebComPyApp(root_component=AppRoot)\n"
        )

    def test_defaults(self, tmp_path):
        mod = self._make_module(tmp_path, self._full_app_code())
        config = WebComPyBuildConfig(app_module=mod)
        assert config.dependencies is None
        assert config.resources is None
        assert config.resource_exclude is None
        assert config.version is None
        assert config.wasm_serving == "cdn"
        assert config.runtime_serving == "cdn"
        assert config.wheel_mode == "bundled"
        assert config.standalone is False
        assert config.serve_all_deps is True
        assert config.dist == "dist"
        assert config.cname == ""
        assert config.static_files_dir == "static"
        assert isinstance(config.server, WebComPyServerConfig)
        assert isinstance(config.app_package_path, Path)

    def test_dependencies(self, tmp_path):
        mod = self._make_module(tmp_path, self._full_app_code())
        config = WebComPyBuildConfig(app_module=mod, dependencies=["numpy", "pandas"])
        assert config.dependencies == ["numpy", "pandas"]

    def test_resources(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, resources=["**/*.html"])
        assert config.resources == ["**/*.html"]

    def test_resource_exclude(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, resource_exclude=["**/secret.html"])
        assert config.resource_exclude == ["**/secret.html"]

    def test_version_field(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, version="1.0.0")
        assert config.version == "1.0.0"

    def test_version_defaults_to_none(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod)
        assert config.version is None

    def test_wasm_serving_defaults_to_cdn(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod)
        assert config.wasm_serving == "cdn"

    def test_wasm_serving_explicit_cdn(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, wasm_serving="cdn")
        assert config.wasm_serving == "cdn"

    def test_wasm_serving_local(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, wasm_serving="local")
        assert config.wasm_serving == "local"

    def test_runtime_serving_defaults_to_cdn(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod)
        assert config.runtime_serving == "cdn"

    def test_runtime_serving_explicit_cdn(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, runtime_serving="cdn")
        assert config.runtime_serving == "cdn"

    def test_runtime_serving_local(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, runtime_serving="local")
        assert config.runtime_serving == "local"

    def test_wheel_mode_defaults_to_bundled(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod)
        assert config.wheel_mode == "bundled"

    def test_wheel_mode_split(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, wheel_mode="split")
        assert config.wheel_mode == "split"

    def test_wheel_mode_bundled_explicit(self, tmp_path):
        mod = self._make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod, wheel_mode="bundled")
        assert config.wheel_mode == "bundled"


class TestLegacyAssetsFieldRemoved:
    def test_assets_kwarg_raises_typeerror(self, tmp_path):
        mod = TestWebComPyBuildConfig()._make_module(tmp_path)
        with pytest.raises(TypeError):
            WebComPyBuildConfig(app_module=mod, assets={"foo": "bar"})


class TestWebComPyServerConfig:
    def test_defaults(self):
        config = WebComPyServerConfig()
        assert config.port == 8080
        assert config.dev is False
        assert config.mounts is None

    def test_custom(self):
        config = WebComPyServerConfig(port=3000, dev=True)
        assert config.port == 3000
        assert config.dev is True

    def test_mounts_callable_not_invoked_at_construction(self):
        from unittest.mock import Mock

        factory = Mock()
        config = WebComPyServerConfig(mounts=factory)
        assert config.mounts is factory
        factory.assert_not_called()


class TestLockfileSyncConfig:
    def test_defaults(self):
        config = LockfileSyncConfig()
        assert config.requirements_path is None
        assert config.sync_group is None

    def test_custom(self):
        config = LockfileSyncConfig(requirements_path="../requirements.txt", sync_group="browser")
        assert config.requirements_path == "../requirements.txt"
        assert config.sync_group == "browser"
