from webcompy.app._config import AppConfig
from webcompy.cli._utils import resolve_standalone_config


class TestAppConfigStandalone:
    def test_default_standalone_false(self):
        config = AppConfig()
        assert config.standalone is False

    def test_standalone_can_be_set(self):
        config = AppConfig(standalone=True)
        assert config.standalone is True

    def test_wasm_serving_default_none(self):
        config = AppConfig()
        assert config.wasm_serving is None

    def test_runtime_serving_default_none(self):
        config = AppConfig()
        assert config.runtime_serving is None


class TestResolveStandaloneConfig:
    def test_standalone_true_sets_defaults(self):
        config = AppConfig(standalone=True)
        resolve_standalone_config(config)
        assert config.serve_all_deps is True
        assert config.wasm_serving == "local"
        assert config.runtime_serving == "local"

    def test_standalone_true_forces_serve_all_deps(self):
        config = AppConfig(standalone=True, serve_all_deps=False)
        resolve_standalone_config(config)
        assert config.serve_all_deps is True

    def test_standalone_true_warns_when_serve_all_deps_false(self, capsys):
        config = AppConfig(standalone=True, serve_all_deps=False)
        resolve_standalone_config(config)
        captured = capsys.readouterr()
        assert "standalone=True forces serve_all_deps=True" in captured.err

    def test_standalone_true_no_warning_when_serve_all_deps_true(self, capsys):
        config = AppConfig(standalone=True, serve_all_deps=True)
        resolve_standalone_config(config)
        captured = capsys.readouterr()
        assert "standalone" not in captured.err

    def test_standalone_true_explicit_wasm_cdn_preserved(self):
        config = AppConfig(standalone=True, wasm_serving="cdn")
        resolve_standalone_config(config)
        assert config.wasm_serving == "cdn"
        assert config.runtime_serving == "local"

    def test_standalone_true_explicit_runtime_cdn_preserved(self):
        config = AppConfig(standalone=True, runtime_serving="cdn")
        resolve_standalone_config(config)
        assert config.runtime_serving == "cdn"
        assert config.wasm_serving == "local"

    def test_standalone_false_resolves_none_to_cdn(self):
        config = AppConfig(standalone=False)
        resolve_standalone_config(config)
        assert config.wasm_serving == "cdn"
        assert config.runtime_serving == "cdn"

    def test_standalone_false_preserves_explicit_local(self):
        config = AppConfig(standalone=False, wasm_serving="local", runtime_serving="local")
        resolve_standalone_config(config)
        assert config.wasm_serving == "local"
        assert config.runtime_serving == "local"

    def test_standalone_true_both_explicit_cdn(self):
        config = AppConfig(standalone=True, wasm_serving="cdn", runtime_serving="cdn")
        resolve_standalone_config(config)
        assert config.wasm_serving == "cdn"
        assert config.runtime_serving == "cdn"
        assert config.serve_all_deps is True

    def test_resolve_idempotent_after_first_call(self):
        config = AppConfig(standalone=True)
        resolve_standalone_config(config)
        first_wasm = config.wasm_serving
        first_runtime = config.runtime_serving
        resolve_standalone_config(config)
        assert config.wasm_serving == first_wasm
        assert config.runtime_serving == first_runtime

    def test_no_duplicate_warning_on_second_call(self, capsys):
        config = AppConfig(standalone=True, serve_all_deps=False)
        resolve_standalone_config(config)
        capsys.readouterr()
        resolve_standalone_config(config)
        captured = capsys.readouterr()
        assert "standalone" not in captured.err

    def test_no_standalone_default_serve_all_deps_true(self):
        config = AppConfig()
        resolve_standalone_config(config)
        assert config.serve_all_deps is True
