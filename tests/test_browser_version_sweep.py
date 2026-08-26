"""Unit tests for the PyScript version-bump sweep diff."""

import json

import pytest

from webcompy_cli._version_sweep import (
    SweepDiff,
    build_sweep_diff,
    diff_probe_reports,
    write_sweep_artifact,
)


def test_diff_buckets_pass_fail_combinations():
    buckets = diff_probe_reports(
        {"a": "passed", "b": "passed", "c": "failed", "d": "failed"},
        {"a": "passed", "b": "failed", "c": "failed", "d": "passed"},
    )

    assert buckets == {
        "only_pinned_pass": ["b"],
        "only_candidate_pass": ["d"],
        "both_pass": ["a"],
        "both_fail": ["c"],
    }


def test_diff_excludes_skipped():
    buckets = diff_probe_reports(
        {"a": "skipped", "b": "passed"},
        {"a": "failed", "b": "passed"},
    )

    assert buckets["only_pinned_pass"] == []
    assert buckets["both_pass"] == ["b"]


def test_regression_is_only_pinned_pass():
    diff = build_sweep_diff(
        "2026.3.1",
        "2026.9.1",
        {"outcomes": {"p1": "passed", "p2": "failed"}},
        {"outcomes": {"p1": "failed", "p2": "passed"}},
    )

    assert diff.regressions == ["p1"]


def test_build_sweep_diff_includes_dualrun_when_both_present():
    pinned = {
        "outcomes": {},
        "cpython_map": {"t": "passed"},
        "pyscript_map": {"t": "passed"},
    }
    candidate = {
        "outcomes": {},
        "cpython_map": {"t": "passed"},
        "pyscript_map": {"t": "failed"},
    }

    diff = build_sweep_diff("p", "c", pinned, candidate, pinned_dualrun=pinned, candidate_dualrun=candidate)

    assert diff.dualrun is not None
    assert diff.dualrun["only_pinned_pass"] == ["t"]


def test_build_sweep_diff_omits_dualrun_without_payloads():
    diff = build_sweep_diff("p", "c", {"outcomes": {}}, {"outcomes": {}})

    assert diff.dualrun is None


def test_write_sweep_artifact_shape(tmp_path):
    diff = SweepDiff(
        pinned_version="2026.3.1",
        candidate_version="2026.9.1",
        probes={"only_pinned_pass": ["probe_b"], "both_pass": ["probe_a"], "only_candidate_pass": [], "both_fail": []},
    )

    path = write_sweep_artifact(diff, tmp_path / "artifacts")

    assert path.name == "browser-version-sweep.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["pinned_version"] == "2026.3.1"
    assert data["candidate_version"] == "2026.9.1"
    assert data["probes"]["only_pinned_pass"] == ["probe_b"]
    assert data["regressions"] == ["probe_b"]
    assert "dualrun" not in data


def test_main_fails_on_regression(tmp_path, capsys):
    pinned = tmp_path / "pinned.json"
    candidate = tmp_path / "candidate.json"
    pinned.write_text(json.dumps({"outcomes": {"p1": "passed"}}), encoding="utf-8")
    candidate.write_text(json.dumps({"outcomes": {"p1": "failed"}}), encoding="utf-8")

    from webcompy_cli._version_sweep import main

    code = main([str(pinned), str(candidate), "--candidate-version", "2026.9.1", "--artifacts-dir", str(tmp_path)])

    assert code == 1


def test_main_passes_without_regression(tmp_path):
    pinned = tmp_path / "pinned.json"
    candidate = tmp_path / "candidate.json"
    pinned.write_text(json.dumps({"outcomes": {"p1": "passed"}}), encoding="utf-8")
    candidate.write_text(json.dumps({"outcomes": {"p1": "passed"}}), encoding="utf-8")

    from webcompy_cli._version_sweep import main

    code = main([str(pinned), str(candidate), "--candidate-version", "2026.9.1", "--artifacts-dir", str(tmp_path)])

    assert code == 0


def test_create_harness_app_threads_candidate_version(monkeypatch, tmp_path):
    import webcompy_cli._browser_test_harness as harness_module
    from webcompy_cli._browser_test_harness import PYSCRIPT_VERSION, create_harness_app

    requested_versions: list[str] = []
    resolved_pyodide: list[str] = []

    def fake_get_pyodide_version(pyscript_version):
        requested_versions.append(pyscript_version)
        return f"pyodide-for-{pyscript_version}"

    def fake_download(pyodide_version, pyscript_version, cache_dir):
        resolved_pyodide.append(pyodide_version)
        return {}

    monkeypatch.setattr(harness_module, "get_pyodide_version", fake_get_pyodide_version)
    monkeypatch.setattr(harness_module, "download_runtime_assets", fake_download)
    monkeypatch.setattr(harness_module, "resolve_pyodide_package_closure", lambda *args, **kwargs: ())
    monkeypatch.setattr(harness_module, "_installable_pyodide_packages", lambda *args, **kwargs: ())
    monkeypatch.setattr(
        harness_module,
        "_ensure_pyodide_package_files",
        lambda *args, **kwargs: None,
    )
    (tmp_path / "tests" / "browser").mkdir(parents=True)

    create_harness_app(tmp_path, tmp_path / "cache", base_url="http://127.0.0.1:1/")
    assert requested_versions[-1] == PYSCRIPT_VERSION
    assert resolved_pyodide[-1] == f"pyodide-for-{PYSCRIPT_VERSION}"

    create_harness_app(
        tmp_path,
        tmp_path / "cache",
        base_url="http://127.0.0.1:1/",
        pyscript_version="2027.1.1",
    )
    assert requested_versions[-1] == "2027.1.1"
    assert resolved_pyodide[-1] == "pyodide-for-2027.1.1"


@pytest.mark.parametrize("payload", ["not json", "{}"])
def test_main_rejects_malformed_reports(tmp_path, payload):
    bad = tmp_path / "bad.json"
    good = tmp_path / "good.json"
    bad.write_text(payload, encoding="utf-8")
    good.write_text('{"outcomes": {}}', encoding="utf-8")

    from webcompy_cli._version_sweep import main

    code = main([str(bad), str(good), "--candidate-version", "x", "--artifacts-dir", str(tmp_path)])

    assert code == 1
