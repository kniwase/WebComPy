"""Unit tests for the browser dual-run AST classifier."""

import json

import pytest

from webcompy_cli._browser_probes import (
    DualRunClassification,
    classify_module,
    classify_tests,
    load_baseline,
    write_baseline,
)


def test_function_local_js_import_is_eligible():
    source = "import asyncio\ndef test_x():\n    import js\n    assert js.document is not None\n"

    assert classify_module(source, "tests/test_x.py") is None


def test_top_level_fake_import_is_ineligible():
    source = "from webcompy_testing import FakeBrowserDOMPort\n"

    reason = classify_module(source, "tests/test_fake.py")

    assert reason is not None
    assert "FakeBrowserDOMPort" in reason


def test_pragma_eligible_overrides_ast_judgment():
    source = "from webcompy_testing import FakeDOMNode\n# browser-dualrun: eligible\n"

    assert classify_module(source, "tests/test_fake.py") is None


def test_pragma_skip_disqualifies_pure_module():
    source = "def test_x():\n    pass\n# browser-dualrun: skip\n"

    reason = classify_module(source, "tests/test_pure.py")

    assert reason is not None
    assert "browser-dualrun: skip" in reason


def test_parametrize_decorator_is_eligible():
    source = 'import pytest\n\n@pytest.mark.parametrize("value", [1, 2])\ndef test_x(value):\n    assert value\n'

    assert classify_module(source, "tests/test_params.py") is None


def test_module_scope_call_is_ineligible():
    source = "from pathlib import Path\nPath('x').exists()\n"

    reason = classify_module(source, "tests/test_side_effect.py")

    assert reason is not None
    assert "module-scope side-effecting call" in reason


def test_assignment_with_call_is_ineligible():
    source = "from pathlib import Path\nHERE = Path(__file__).parent\n"

    reason = classify_module(source, "tests/test_assign.py")

    assert reason is not None
    assert "module-scope side-effecting call" in reason


def test_non_pytest_fixture_call_is_ineligible():
    source = "from unittest.mock import MagicMock\nM = MagicMock()\n"

    assert classify_module(source, "tests/test_mock.py") is not None


def test_non_fake_webcompy_testing_symbol_is_eligible():
    source = "from webcompy_testing import TestRenderer\n"

    assert classify_module(source, "tests/test_renderer.py") is None


def test_e2e_import_is_ineligible():
    source = "from e2e.core.conftest import helper\n"

    reason = classify_module(source, "tests/test_e2e_dep.py")

    assert reason is not None
    assert "e2e" in reason


def test_browser_only_import_is_ineligible():
    source = "from pyodide.ffi import to_js\n"

    reason = classify_module(source, "tests/test_ffi.py")

    assert reason is not None
    assert "pyodide" in reason


def test_syntax_error_is_reported_by_classify_tests(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_broken.py").write_text("def broken(:\n", encoding="utf-8")
    (tmp_path / "tests" / "test_ok.py").write_text("def test_ok(): pass\n", encoding="utf-8")

    result = classify_tests(tmp_path)

    assert result.eligible == ["tests/test_ok.py"]
    assert list(result.ineligible) == ["tests/test_broken.py"]
    assert "syntax error" in result.ineligible["tests/test_broken.py"]


def test_classify_tests_skips_browser_tier_and_sorts(tmp_path):
    tests = tmp_path / "tests"
    (tests / "browser").mkdir(parents=True)
    (tests / "browser" / "test_dom_browser.py").write_text("x = 1\n", encoding="utf-8")
    (tests / "test_z.py").write_text("x = 1\n", encoding="utf-8")
    (tests / "test_a.py").write_text("x = 1\n", encoding="utf-8")

    result = classify_tests(tmp_path)

    assert result.eligible == ["tests/test_a.py", "tests/test_z.py"]
    assert "tests/browser/test_dom_browser.py" not in result.eligible


def test_write_baseline_shapes_and_sorting(tmp_path):
    result = DualRunClassification(
        eligible=["tests/b.py", "tests/a.py"],
        ineligible={"tests/d.py": "reason d", "tests/c.py": "reason c"},
    )

    eligible_path, ineligible_path = write_baseline(result, tmp_path)

    assert eligible_path.read_text(encoding="utf-8") == "tests/a.py\ntests/b.py\n"
    data = json.loads(ineligible_path.read_text(encoding="utf-8"))
    assert data == {"tests/c.py": "reason c", "tests/d.py": "reason d"}


def test_load_baseline_missing_file_returns_empty(tmp_path):
    assert load_baseline(tmp_path) == []


def test_load_baseline_reads_sorted_lines(tmp_path):
    baseline_dir = tmp_path / "tests" / ".dualrun"
    baseline_dir.mkdir(parents=True)
    (baseline_dir / "eligible.txt").write_text("tests/b.py\ntests/a.py\n\n", encoding="utf-8")

    assert load_baseline(tmp_path) == ["tests/a.py", "tests/b.py"]


@pytest.mark.parametrize(
    ("source", "expected_eligible"),
    [
        ('X: int = 1\nY = "const"\n', True),
        ("class Foo:\n    x = Path('y')\n", True),
        ("@custom_decorator\ndef test_x(): pass\n", True),
        ("@custom_decorator('arg')\ndef test_x(): pass\n", False),
    ],
)
def test_statement_classification_matrix(source, expected_eligible):
    needs_import = "custom_decorator" in source
    if needs_import:
        source = f"from custom import custom_decorator\n{source}"

    reason = classify_module(source, "tests/test_matrix.py")

    assert (reason is None) is expected_eligible
