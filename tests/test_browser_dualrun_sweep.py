"""Unit tests for the browser dual-run sweep helpers and harness merge."""

import json
from pathlib import Path

from webcompy_cli._browser_probes import (
    DualRunSweepResult,
    convert_cpython_id,
    diff_outcomes,
    write_dualrun_artifact,
)
from webcompy_cli._browser_test_harness import build_py_config, merge_test_relpaths

BASE_URL = "http://127.0.0.1:8123/"


def test_convert_plain_nodeid_unchanged():
    assert convert_cpython_id("tests/test_x.py::test_a", {}) == "tests/test_x.py::test_a"


def test_convert_parametrized_id_uses_index_form():
    indices = {"tests/test_x.py::test_a": 2}

    converted = convert_cpython_id("tests/test_x.py::test_a[some value]", indices)

    assert converted == "tests/test_x.py::test_a[p2]"


def test_convert_unknown_index_strips_suffix():
    converted = convert_cpython_id("tests/test_x.py::test_b[1]", {})

    assert converted == "tests/test_x.py::test_b"


def test_diff_outcomes_buckets_pass_fail_pairs():
    buckets = diff_outcomes(
        {"a": "passed", "b": "passed", "c": "failed", "d": "failed"},
        {"a": "passed", "b": "failed", "c": "failed", "d": "passed"},
    )

    assert buckets == {
        "both-pass": ["a"],
        "CPython-only-fail": ["d"],
        "PyScript-only-fail": ["b"],
        "both-fail": ["c"],
    }


def test_diff_outcomes_excludes_skipped_from_buckets():
    buckets = diff_outcomes(
        {"a": "skipped", "b": "passed"},
        {"a": "failed", "b": "passed"},
    )

    assert buckets["both-pass"] == ["b"]
    assert all(bucket == [] for name, bucket in buckets.items() if name != "both-pass")


def test_write_dualrun_artifact_shape(tmp_path):
    result = DualRunSweepResult(
        eligible_count=2,
        buckets={"both-pass": ["a"], "PyScript-only-fail": []},
        cpython_map={"a": "passed"},
        pyscript_map={"a": "passed"},
        duration_ms=12.3456,
    )

    path = write_dualrun_artifact(result, tmp_path / "artifacts")

    data = json.loads(path.read_text(encoding="utf-8"))
    assert path.name == "browser-dualrun.json"
    assert data["eligible_count"] == 2
    assert data["buckets"]["both-pass"] == ["a"]
    assert data["cpython_map"] == {"a": "passed"}
    assert data["pyscript_map"] == {"a": "passed"}
    assert isinstance(data["duration_ms"], float)


def test_write_dualrun_artifact_includes_error(tmp_path):
    result = DualRunSweepResult(eligible_count=0, error="CPython collection failed")
    path = write_dualrun_artifact(result, tmp_path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["error"] == "CPython collection failed"


def test_merge_test_relpaths_without_dual_returns_browser_only(tmp_path):
    (tmp_path / "tests" / "browser").mkdir(parents=True)
    (tmp_path / "tests" / "browser" / "test_a.py").write_text("", encoding="utf-8")
    (tmp_path / "tests" / "__init__.py").write_text("", encoding="utf-8")

    merged = merge_test_relpaths(tmp_path, None)

    assert merged == ["tests/browser/test_a.py"]


def test_merge_test_relpaths_adds_eligible_and_package_markers(tmp_path):
    tests = tmp_path / "tests"
    (tests / "browser").mkdir(parents=True)
    (tests / "conformance").mkdir(parents=True)
    (tests / "browser" / "test_a.py").write_text("", encoding="utf-8")
    (tests / "__init__.py").write_text("", encoding="utf-8")
    (tests / "conformance" / "__init__.py").write_text("", encoding="utf-8")

    merged = merge_test_relpaths(
        tmp_path,
        [
            "tests/conformance/test_gfm_spec.py",
            "tests/test_signal.py",
            "tests/browser/test_a.py",
        ],
    )

    assert merged == [
        "tests/__init__.py",
        "tests/browser/test_a.py",
        "tests/conformance/__init__.py",
        "tests/conformance/test_gfm_spec.py",
        "tests/test_signal.py",
    ]


def test_merge_test_relpaths_deduplicates_and_skips_missing_inits(tmp_path):
    (tmp_path / "tests").mkdir()

    merged = merge_test_relpaths(tmp_path, ["tests/test_signal.py"])

    # No tests/__init__.py on disk -> only the eligible path itself is added.
    assert merged == ["tests/test_signal.py"]


def test_build_py_config_accepts_merged_relpaths():
    config = build_py_config(
        base_url=BASE_URL,
        supply_mode="wheel",
        wheel_names=["w.whl"],
        test_relpaths=[
            "tests/browser/test_a.py",
            "tests/__init__.py",
            "tests/test_signal.py",
        ],
    )

    files = config["files"]
    assert files[f"{BASE_URL}_webcompy-test/files/tests/test_signal.py"] == "/home/pyodide/tests/test_signal.py"
    assert files[f"{BASE_URL}_webcompy-test/files/tests/__init__.py"] == "/home/pyodide/tests/__init__.py"


def _make_repo_with_tests(root: Path, modules: dict[str, str]) -> None:
    for rel, content in modules.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


class _FakeDriver:
    def __init__(self, statuses: dict[str, str]):
        self.statuses = statuses
        self.calls: list[str] = []

    def run_one(self, test_id: str) -> str:
        self.calls.append(test_id)
        return json.dumps({"status": self.statuses.get(test_id, "passed")})


def test_run_dualrun_sweep_end_to_end_with_fake_driver(tmp_path, monkeypatch):
    from webcompy_cli._browser_probes import run_dualrun_sweep

    monkeypatch.chdir(tmp_path)
    _make_repo_with_tests(
        tmp_path,
        {
            "tests/test_ok.py": "def test_one(): pass\n",
            "tests/test_mixed.py": (
                'import pytest\n\n\n@pytest.mark.parametrize("v", [1, 2])\ndef test_pair(v):\n    assert v\n'
            ),
        },
    )
    driver = _FakeDriver({})

    result = run_dualrun_sweep(repo_root=tmp_path, driver=driver, artifacts_dir=tmp_path / "artifacts")

    assert result.error is None
    assert result.eligible_count == 2
    assert set(result.cpython_map) >= {
        "tests/test_ok.py::test_one",
        "tests/test_mixed.py::test_pair[1]",
        "tests/test_mixed.py::test_pair[2]",
    }
    assert result.buckets["both-pass"]
    artifact = json.loads((tmp_path / "artifacts" / "browser-dualrun.json").read_text(encoding="utf-8"))
    assert artifact["eligible_count"] == result.eligible_count
    # The parametrized ids must be dispatched in the machine index form.
    assert any(call.endswith("[p0]") or call.endswith("[p1]") for call in driver.calls)


def test_run_dualrun_sweep_records_pyscript_divergence(tmp_path, monkeypatch):
    from webcompy_cli._browser_probes import run_dualrun_sweep

    monkeypatch.chdir(tmp_path)
    _make_repo_with_tests(tmp_path, {"tests/test_ok.py": "def test_one(): pass\n"})

    class _FailingDriver:
        def run_one(self, test_id: str) -> str:
            return json.dumps({"status": "failed"})

    result = run_dualrun_sweep(
        repo_root=tmp_path,
        driver=_FailingDriver(),
        artifacts_dir=tmp_path / "artifacts",
    )

    assert result.buckets["PyScript-only-fail"] == ["tests/test_ok.py::test_one"]
    assert result.cpython_map["tests/test_ok.py::test_one"] == "passed"
