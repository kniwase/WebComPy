import pytest

from tests.browser._driver import (
    append_param_index,
    classify_crash,
    normalize_traceback_paths,
    sentinel_timeout_seconds,
    strip_param_suffix,
)


class TestClassifyCrash:
    @pytest.mark.parametrize(
        ("exc_text", "expected"),
        [
            ("Target page, context or browser has been closed", True),
            ("Page.evaluate: Target closed", True),
            ("Aborted(Assertion failed). Build with -s ASSERTIONS=1", True),
            ("TypeError: cannot read properties of undefined", False),
        ],
    )
    def test_exc_text(self, exc_text, expected):
        assert classify_crash(exc_text, []) is expected

    def test_wasm_abort_visible_only_in_console_tail(self):
        assert classify_crash("some evaluate error", ["Aborted(1). Build with -s"]) is True

    def test_plain_failure_is_not_a_crash(self):
        assert classify_crash("AssertionError", []) is False


class TestNormalizeTracebackPaths:
    def test_tests_root(self):
        assert (
            normalize_traceback_paths('File "/home/pyodide/tests/browser/test_a.py"')
            == 'File "tests/browser/test_a.py"'
        )

    def test_framework_trees(self):
        rewritten = normalize_traceback_paths(
            "/home/pyodide/_wc_src/webcompy/signal/_graph.py "
            "/home/pyodide/_wc_src/webcompy_testing/browser_runner/x.py "
            "/home/pyodide/_wc_src/webcompy_server/ports/y.py"
        )

        assert "packages/webcompy/src/webcompy/signal/_graph.py" in rewritten
        assert "packages/webcompy-testing/src/webcompy_testing/browser_runner/x.py" in rewritten
        assert "packages/webcompy-server/src/webcompy_server/ports/y.py" in rewritten


class TestParamIndexSuffix:
    def test_round_trip(self):
        suffixed = append_param_index("tests/browser/t.py::test_foo[a-b]", 2)

        node_id, index = strip_param_suffix(suffixed)

        assert node_id == "tests/browser/t.py::test_foo[a-b]"
        assert index == 2

    def test_no_suffix(self):
        node_id, index = strip_param_suffix("tests/browser/t.py::test_bar")

        assert node_id == "tests/browser/t.py::test_bar"
        assert index is None


def test_sentinel_timeout_default(monkeypatch):
    monkeypatch.delenv("WEBCOMPY_BROWSER_SENTINEL_TIMEOUT", raising=False)

    assert sentinel_timeout_seconds() == 120.0


def test_sentinel_timeout_env_override(monkeypatch):
    monkeypatch.setenv("WEBCOMPY_BROWSER_SENTINEL_TIMEOUT", "15")

    assert sentinel_timeout_seconds() == 15.0


def test_sentinel_timeout_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("WEBCOMPY_BROWSER_SENTINEL_TIMEOUT", "abc")

    assert sentinel_timeout_seconds() == 120.0
