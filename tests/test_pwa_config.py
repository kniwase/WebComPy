from __future__ import annotations

from pathlib import Path

import pytest

from webcompy.exception import WebComPyException
from webcompy_cli.config import (
    ManifestConfig,
    ManifestIcon,
    PWAConfig,
    RuntimeCachingRule,
    WebComPyBuildConfig,
)
from webcompy_cli.config._build_config import WebComPyBuildConfig as BuildConfigDirect


def _make_module(tmp_path: Path):
    mod_path = tmp_path / "app_mod.py"
    mod_path.write_text("app = None\n", encoding="utf-8")
    import importlib
    import sys

    sys.path.insert(0, str(tmp_path))
    try:
        return importlib.import_module("app_mod")
    finally:
        sys.path.pop(0)


def _validate(config: PWAConfig, tmp_path: Path, static_files_dir: str = "static") -> None:
    config.validate(app_package_path=tmp_path, static_files_dir=static_files_dir)


class TestManifestConfig:
    def test_defaults(self):
        manifest = ManifestConfig(name="My App")
        assert manifest.short_name is None
        assert manifest.icons == []
        assert manifest.display == "standalone"
        assert manifest.theme_color is None
        assert manifest.background_color is None
        assert manifest.start_url is None
        assert manifest.scope is None

    def test_icon_defaults(self):
        icon = ManifestIcon(src="icons/app.png", sizes="512x512")
        assert icon.type is None
        assert icon.purpose is None


class TestPWAConfigDefaults:
    def test_defaults(self):
        pwa = PWAConfig()
        assert pwa.enabled is False
        assert pwa.manifest is None
        assert pwa.precache == "auto"
        assert pwa.precache_runtime is False
        assert pwa.runtime == []
        assert pwa.fallback_path is None

    def test_rule_fields(self):
        rule = RuntimeCachingRule(pattern="/api/", strategy="network-first", max_entries=50, max_age=60)
        assert rule.pattern == "/api/"
        assert rule.strategy == "network-first"
        assert rule.max_entries == 50
        assert rule.max_age == 60

    def test_build_config_default_pwa(self, tmp_path):
        mod = _make_module(tmp_path)
        config = WebComPyBuildConfig(app_module=mod)
        assert isinstance(config.pwa, PWAConfig)
        assert config.pwa.enabled is False

    def test_build_config_custom_pwa(self, tmp_path):
        mod = _make_module(tmp_path)
        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="A"))
        config = WebComPyBuildConfig(app_module=mod, pwa=pwa)
        assert config.pwa is pwa

    def test_module_aliases_match(self):
        assert BuildConfigDirect is WebComPyBuildConfig


class TestPWAValidate:
    def test_disabled_is_noop(self, tmp_path):
        _validate(PWAConfig(precache="none", precache_runtime=True), tmp_path)

    def test_requires_manifest_when_enabled(self, tmp_path):
        with pytest.raises(WebComPyException, match="no manifest is configured"):
            _validate(PWAConfig(enabled=True), tmp_path)

    def test_valid_enabled_config_passes(self, tmp_path):
        _validate(PWAConfig(enabled=True, manifest=ManifestConfig(name="A")), tmp_path)

    def test_rejects_invalid_precache_mode(self, tmp_path):
        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="A"))
        pwa.precache = "smart"  # type: ignore[assignment]
        with pytest.raises(WebComPyException, match="precache"):
            _validate(pwa, tmp_path)

    def test_rejects_none_precache_with_runtime(self, tmp_path):
        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="A"), precache="none", precache_runtime=True)
        with pytest.raises(WebComPyException, match="precache_runtime cannot be enabled"):
            _validate(pwa, tmp_path)

    def test_rejects_invalid_display(self, tmp_path):
        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="A", display="kiosk"))
        with pytest.raises(WebComPyException, match="display"):
            _validate(pwa, tmp_path)

    def test_rejects_empty_rule_pattern(self, tmp_path):
        pwa = PWAConfig(
            enabled=True,
            manifest=ManifestConfig(name="A"),
            runtime=[RuntimeCachingRule(pattern="", strategy="cache-first")],
        )
        with pytest.raises(WebComPyException, match=r"runtime\[0\]\.pattern"):
            _validate(pwa, tmp_path)

    def test_rejects_cross_origin_rule_pattern(self, tmp_path):
        pwa = PWAConfig(
            enabled=True,
            manifest=ManifestConfig(name="A"),
            runtime=[RuntimeCachingRule(pattern="https://cdn.example.com/", strategy="cache-first")],
        )
        with pytest.raises(WebComPyException, match="same-origin"):
            _validate(pwa, tmp_path)

    def test_rejects_unknown_strategy(self, tmp_path):
        pwa = PWAConfig(
            enabled=True,
            manifest=ManifestConfig(name="A"),
            runtime=[RuntimeCachingRule(pattern="/api/", strategy="always-cache")],  # type: ignore[arg-type]
        )
        with pytest.raises(WebComPyException, match="strategy is invalid"):
            _validate(pwa, tmp_path)

    @pytest.mark.parametrize("key", ["max_entries", "max_age"])
    @pytest.mark.parametrize("value", [0, -1, True, "30"])
    def test_rejects_invalid_limits(self, tmp_path, key, value):
        rule = RuntimeCachingRule(pattern="/api/", strategy="cache-first", **{key: value})
        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="A"), runtime=[rule])
        with pytest.raises(WebComPyException, match=key):
            _validate(pwa, tmp_path)

    def test_accepts_valid_rule_limits(self, tmp_path):
        pwa = PWAConfig(
            enabled=True,
            manifest=ManifestConfig(name="A"),
            runtime=[
                RuntimeCachingRule(pattern="/api/", strategy="stale-while-revalidate", max_entries=10, max_age=86400)
            ],
        )
        _validate(pwa, tmp_path)

    def test_rejects_absolute_fallback_path(self, tmp_path):
        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="A"), fallback_path="/offline.html")
        with pytest.raises(WebComPyException, match="relative path"):
            _validate(pwa, tmp_path)

    def test_rejects_traversal_fallback_path(self, tmp_path):
        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="A"), fallback_path="../offline.html")
        with pytest.raises(WebComPyException, match="relative path"):
            _validate(pwa, tmp_path)

    def test_rejects_missing_fallback_file(self, tmp_path):
        (tmp_path / "static").mkdir()
        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="A"), fallback_path="offline.html")
        with pytest.raises(WebComPyException, match="does not exist"):
            _validate(pwa, tmp_path)

    def test_accepts_existing_fallback_file(self, tmp_path):
        static = tmp_path / "static"
        static.mkdir()
        (static / "offline.html").write_text("<html></html>", encoding="utf-8")
        pwa = PWAConfig(enabled=True, manifest=ManifestConfig(name="A"), fallback_path="offline.html")
        _validate(pwa, tmp_path)
