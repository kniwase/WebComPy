from webcompy.cli.config._build_config import WebComPyBuildConfig


class _FakeModule:
    def __init__(self):
        self.__file__ = __file__
        self.app = None


def _make_config(**kwargs):
    return WebComPyBuildConfig(app_module=_FakeModule(), **kwargs)


class TestWebComPyBuildConfigStandalone:
    def test_default_standalone_false(self):
        config = _make_config()
        assert config.standalone is False

    def test_standalone_can_be_set(self):
        config = _make_config(standalone=True)
        assert config.standalone is True

    def test_wasm_serving_default_cdn_when_not_standalone(self):
        config = _make_config()
        assert config.wasm_serving == "cdn"

    def test_runtime_serving_default_cdn_when_not_standalone(self):
        config = _make_config()
        assert config.runtime_serving == "cdn"


class TestResolveStandaloneConfig:
    def test_standalone_true_sets_defaults(self):
        config = _make_config(standalone=True)
        assert config.serve_all_deps is True
        assert config.wasm_serving == "local"
        assert config.runtime_serving == "local"

    def test_standalone_true_forces_serve_all_deps(self):
        config = _make_config(standalone=True, serve_all_deps=False)
        assert config.serve_all_deps is True

    def test_standalone_true_warns_when_serve_all_deps_false(self, capsys):
        _ = _make_config(standalone=True, serve_all_deps=False)
        captured = capsys.readouterr()
        assert "standalone=True forces serve_all_deps=True" in captured.err

    def test_standalone_true_no_warning_when_serve_all_deps_true(self, capsys):
        _ = _make_config(standalone=True, serve_all_deps=True)
        captured = capsys.readouterr()
        assert "standalone" not in captured.err

    def test_standalone_true_explicit_wasm_cdn_preserved(self):
        config = _make_config(standalone=True, wasm_serving="cdn")
        assert config.wasm_serving == "cdn"
        assert config.runtime_serving == "local"

    def test_standalone_true_explicit_runtime_cdn_preserved(self):
        config = _make_config(standalone=True, runtime_serving="cdn")
        assert config.runtime_serving == "cdn"
        assert config.wasm_serving == "local"

    def test_standalone_false_resolves_none_to_cdn(self):
        config = _make_config(standalone=False)
        assert config.wasm_serving == "cdn"
        assert config.runtime_serving == "cdn"

    def test_standalone_false_preserves_explicit_local(self):
        config = _make_config(standalone=False, wasm_serving="local", runtime_serving="local")
        assert config.wasm_serving == "local"
        assert config.runtime_serving == "local"

    def test_standalone_true_both_explicit_cdn(self):
        config = _make_config(standalone=True, wasm_serving="cdn", runtime_serving="cdn")
        assert config.wasm_serving == "cdn"
        assert config.runtime_serving == "cdn"
        assert config.serve_all_deps is True

    def test_resolve_idempotent_after_first_call(self):
        config = _make_config(standalone=True)
        first_wasm = config.wasm_serving
        first_runtime = config.runtime_serving
        config2 = _make_config(standalone=True)
        assert config2.wasm_serving == first_wasm
        assert config2.runtime_serving == first_runtime

    def test_no_duplicate_warning_on_second_call(self, capsys):
        capsys.readouterr()
        _ = _make_config(standalone=True, serve_all_deps=False)
        captured = capsys.readouterr()
        assert "standalone=True forces serve_all_deps=True" in captured.err
        _ = _make_config(standalone=True, serve_all_deps=False)
        captured2 = capsys.readouterr()
        assert "standalone=True forces serve_all_deps=True" in captured2.err

    def test_no_standalone_default_serve_all_deps_true(self):
        config = _make_config()
        assert config.serve_all_deps is True
