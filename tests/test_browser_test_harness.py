import html
import json

from webcompy_cli._browser_test_harness import (
    bootstrap_lines,
    build_py_config,
    collect_framework_source_files,
    discover_test_modules,
    generate_harness_html,
    resolve_supply_mode,
)

BASE_URL = "http://127.0.0.1:8123/"


def test_resolve_supply_mode_default(monkeypatch):
    monkeypatch.delenv("WEBCOMPY_BROWSER_SOURCE", raising=False)
    assert resolve_supply_mode() == "wheel"


def test_resolve_supply_mode_source(monkeypatch):
    monkeypatch.setenv("WEBCOMPY_BROWSER_SOURCE", "1")
    assert resolve_supply_mode() == "source"


def test_discover_test_modules(tmp_path):
    browser_dir = tmp_path / "tests" / "browser"
    nested = browser_dir / "sub"
    nested.mkdir(parents=True)
    (browser_dir / "test_b.py").write_text("")
    (browser_dir / "test_a.py").write_text("")
    (nested / "test_c.py").write_text("")
    (browser_dir / "helper.py").write_text("")
    (browser_dir / "conftest.py").write_text("")

    discovered = discover_test_modules(tmp_path)

    assert [p.as_posix() for p in discovered] == [
        "tests/browser/sub/test_c.py",
        "tests/browser/test_a.py",
        "tests/browser/test_b.py",
    ]


def test_discover_test_modules_missing_dir(tmp_path):
    assert discover_test_modules(tmp_path) == []


def test_collect_framework_source_files(tmp_path):
    src_root = tmp_path / "packages" / "webcompy" / "src"
    tree = src_root / "webcompy"
    (tree / "signal").mkdir(parents=True)
    (tree / "__init__.py").write_text("")
    (tree / "signal" / "__init__.py").write_text("")
    (tree / "signal" / "__pycache__").mkdir()
    (tree / "signal" / "__pycache__" / "x.py").write_text("")

    result = collect_framework_source_files(tmp_path)

    assert result["webcompy"] == ["webcompy/__init__.py", "webcompy/signal/__init__.py"]


def test_build_py_config_wheel_mode():
    config = build_py_config(
        base_url=BASE_URL,
        supply_mode="wheel",
        wheel_names=["webcompy-0+sha.abcd-py3-none-any.whl"],
        test_relpaths=["tests/browser/test_a.py"],
    )

    assert config["experimental_create_proxy"] == "auto"
    assert config["packages"] == ["http://127.0.0.1:8123/_webcompy-test/wheels/webcompy-0+sha.abcd-py3-none-any.whl"]
    assert config["files"] == {
        "http://127.0.0.1:8123/_webcompy-test/files/tests/browser/test_a.py": ("/home/pyodide/tests/browser/test_a.py")
    }
    assert config["interpreter"] == "http://127.0.0.1:8123/_webcompy-assets/pyodide/pyodide.mjs"
    assert config["lockFileURL"] == "http://127.0.0.1:8123/_webcompy-assets/pyodide/pyodide-lock.json"


def test_build_py_config_source_mode():
    framework_files = {"webcompy": ["webcompy/__init__.py", "webcompy/signal/__init__.py"]}
    config = build_py_config(
        base_url=BASE_URL,
        supply_mode="source",
        wheel_names=[],
        test_relpaths=["tests/browser/test_a.py"],
        framework_files=framework_files,
    )

    assert "packages" not in config
    files = config["files"]
    assert (
        files["http://127.0.0.1:8123/_webcompy-test/files/webcompy/webcompy/signal/__init__.py"]
        == "/home/pyodide/_wc_src/webcompy/signal/__init__.py"
    )
    assert (
        files["http://127.0.0.1:8123/_webcompy-test/files/tests/browser/test_a.py"]
        == "/home/pyodide/tests/browser/test_a.py"
    )
    for key, dest in files.items():
        assert key.startswith("http://")
        assert dest.startswith("/home/pyodide/")


def test_generate_harness_html_parity_and_order():
    py_config = build_py_config(
        base_url=BASE_URL,
        supply_mode="wheel",
        wheel_names=["x.whl"],
        test_relpaths=["tests/browser/test_a.py"],
    )
    page = generate_harness_html(py_config, base_url=BASE_URL, source_mounted=False)

    expected_attr = html.escape(json.dumps(py_config), quote=True)
    assert f'config="{expected_attr}"' in page
    collector_index = page.index("__webcompy_test_console__")
    py_script_index = page.index('<script type="py"')
    assert collector_index < py_script_index
    assert 'src="http://127.0.0.1:8123/_webcompy-assets/core.js"' in page
    assert 'href="http://127.0.0.1:8123/_webcompy-assets/core.css"' in page
    assert '<div id="webcompy-app"></div>' in page


def test_bootstrap_lines_wheel_mode():
    lines = bootstrap_lines("wheel")

    assert 'sys.path.insert(0, "/home/pyodide")' in lines
    assert "_wc_src" not in lines
    assert "from webcompy_testing.browser_runner import bootstrap" in lines
    assert lines.rstrip().endswith("bootstrap()")


def test_bootstrap_lines_source_mode():
    lines = bootstrap_lines("source")

    assert 'sys.path.insert(0, "/home/pyodide/_wc_src")' in lines
    assert 'sys.path.insert(0, "/home/pyodide")' in lines
