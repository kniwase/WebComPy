import pytest

from webcompy_testing.browser_runner import (
    UnknownFixtureError,
    normalize_traceback,
    parse_test_id,
    resolve_parametrize_payload,
)


class TestParseTestId:
    def test_plain_node_id(self):
        module_name, qualname, index = parse_test_id("tests/browser/test_signal_browser.py::test_signal_roundtrip")

        assert module_name == "tests.browser.test_signal_browser"
        assert qualname == "test_signal_roundtrip"
        assert index is None

    def test_param_index_suffix(self):
        module_name, qualname, index = parse_test_id("tests/browser/test_dom_browser.py::Class::method[p3]")

        assert module_name == "tests.browser.test_dom_browser"
        assert qualname == "Class::method"
        assert index == 3

    def test_pytest_display_ids_are_preserved(self):
        module_name, qualname, _ = parse_test_id("tests/browser/test_x.py::test_foo[a-b][p1]")

        assert module_name == "tests.browser.test_x"
        assert qualname == "test_foo[a-b]"

    def test_malformed_id_raises(self):
        with pytest.raises(ValueError, match="malformed test id"):
            parse_test_id("tests/browser/test_x.py")


class TestNormalizeTraceback:
    def test_tests_root_rewrite(self):
        normalized = normalize_traceback('File "/home/pyodide/tests/browser/test_a.py", line 1')

        assert 'File "tests/browser/test_a.py", line 1' in normalized

    def test_framework_tree_rewrites(self):
        normalized = normalize_traceback(
            "/home/pyodide/_wc_src/webcompy/signal/_graph.py "
            "/home/pyodide/_wc_src/webcompy_testing/x.py "
            "/home/pyodide/_wc_src/webcompy_server/ports/y.py"
        )

        assert "packages/webcompy/src/webcompy/signal/_graph.py" in normalized
        assert "packages/webcompy-testing/src/webcompy_testing/x.py" in normalized
        assert "packages/webcompy-server/src/webcompy_server/ports/y.py" in normalized


def _marked(names, values):
    def func(a):
        return a

    func.pytestmark = [type("M", (), {"name": "parametrize", "args": (names, values)})()]
    return func


class TestResolveParametrizePayload:
    def test_single_argname(self):
        func = _marked("value", [1, 2])

        assert resolve_parametrize_payload(func, 0) == {"value": 1}
        assert resolve_parametrize_payload(func, 1) == {"value": 2}

    def test_multiple_argnames(self):
        func = _marked(("a", "b"), [(1, "x"), (2, "y")])

        assert resolve_parametrize_payload(func, 1) == {"a": 2, "b": "y"}

    def test_no_mark_no_index(self):
        def plain():
            return None

        assert resolve_parametrize_payload(plain, None) == {}

    def test_index_without_mark_raises(self):
        def plain():
            return None

        with pytest.raises(ValueError, match="no parametrize mark"):
            resolve_parametrize_payload(plain, 0)

    def test_mark_without_index_raises(self):
        func = _marked("value", [1])

        with pytest.raises(ValueError, match="without a"):
            resolve_parametrize_payload(func, None)

    def test_stacked_marks_raise(self):
        func = _marked("value", [1])
        func.pytestmark.append(type("M", (), {"name": "parametrize", "args": ("other", [9])})())

        with pytest.raises(ValueError, match="stacked"):
            resolve_parametrize_payload(func, 0)


class TestUnknownFixtureError:
    def test_message_names_fixture_and_registry(self):
        error = UnknownFixtureError("browser")

        assert "'browser'" in str(error)
        assert "app" in str(error)
        assert "dom_root" in str(error)
