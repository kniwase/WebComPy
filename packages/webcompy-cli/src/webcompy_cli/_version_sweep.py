"""Version-bump sweep: diff probe (and dual-run) outcomes across two PyScript versions.

The sweep executes the probe battery twice with the same harness code — once
against the pinned runtime assets and once against a candidate version's
assets (downloaded via the existing runtime downloader when
``WEBCOMPY_PYSCRIPT_CANDIDATE`` is set) — and buckets each probe id into
``only_pinned_pass`` / ``only_candidate_pass`` / ``both_pass`` / ``both_fail``.
A probe that passes at the pinned version but fails at the candidate is a
regression and fails the sweep. Candidate assets are never promoted
automatically; the sweep is informational except for regressions.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

SWEEP_ARTIFACT_NAME = "browser-version-sweep.json"

PROBE_BUCKETS = ("only_pinned_pass", "only_candidate_pass", "both_pass", "both_fail")


@dataclass
class SweepDiff:
    """Bucketed diff of probe outcomes between two PyScript versions.

    Attributes:
        pinned_version: Pinned ``PYSCRIPT_VERSION`` string.
        candidate_version: Candidate version string under evaluation.
        probes: Probe-id buckets keyed ``only_pinned_pass``,
            ``only_candidate_pass``, ``both_pass``, and ``both_fail``.
        dualrun: Same bucket shape for the dual-run tier when both runs
            produced dual-run reports; ``None`` otherwise.

    """

    pinned_version: str
    candidate_version: str
    probes: dict[str, list[str]] = field(default_factory=dict)
    dualrun: dict[str, list[str]] | None = None

    @property
    def regressions(self) -> list[str]:
        """Probe ids that passed at the pinned version but fail at the candidate."""
        return list(self.probes.get("only_pinned_pass", []))


def diff_probe_reports(
    pinned_outcomes: dict[str, str],
    candidate_outcomes: dict[str, str],
) -> dict[str, list[str]]:
    """Bucket probe ids by pass/fail combination across two versions.

    Args:
        pinned_outcomes: Probe-id-to-outcome mapping at the pinned version.
        candidate_outcomes: Same-shaped mapping at the candidate version.

    Returns:
        Buckets keyed ``only_pinned_pass``, ``only_candidate_pass``,
        ``both_pass``, and ``both_fail``; skipped probes are excluded.

    """
    buckets: dict[str, list[str]] = {name: [] for name in PROBE_BUCKETS}
    for probe_id in sorted(set(pinned_outcomes) & set(candidate_outcomes)):
        pinned_passed = pinned_outcomes[probe_id] == "passed"
        candidate_passed = candidate_outcomes[probe_id] == "passed"
        if pinned_outcomes[probe_id] == "skipped" or candidate_outcomes[probe_id] == "skipped":
            continue
        if pinned_passed and candidate_passed:
            buckets["both_pass"].append(probe_id)
        elif pinned_passed:
            buckets["only_pinned_pass"].append(probe_id)
        elif candidate_passed:
            buckets["only_candidate_pass"].append(probe_id)
        else:
            buckets["both_fail"].append(probe_id)
    return buckets


def build_sweep_diff(
    pinned_version: str,
    candidate_version: str,
    pinned_report: dict,
    candidate_report: dict,
    *,
    pinned_dualrun: dict | None = None,
    candidate_dualrun: dict | None = None,
) -> SweepDiff:
    """Assemble a :class:`SweepDiff` from two plugin outcome reports.

    Args:
        pinned_version: Pinned version identifier.
        candidate_version: Candidate version identifier.
        pinned_report: Plugin report (``outcomes`` mapping) at the pin.
        candidate_report: Plugin report at the candidate version.
        pinned_dualrun: Optional dual-run artifact payload at the pin.
        candidate_dualrun: Optional dual-run artifact payload at the candidate.

    Returns:
        The assembled diff including dual-run buckets when both payloads are
        present and share test ids.

    """
    diff = SweepDiff(
        pinned_version=pinned_version,
        candidate_version=candidate_version,
        probes=diff_probe_reports(pinned_report["outcomes"], candidate_report["outcomes"]),
    )
    if pinned_dualrun is not None and candidate_dualrun is not None:
        cpython = pinned_dualrun.get("cpython_map", {})

        def normalize(outcome: str) -> str:
            return outcome if outcome in ("passed", "failed", "skipped") else "failed"

        pinned_in_page = {
            test_id: normalize(outcome)
            for test_id, outcome in pinned_dualrun.get("pyscript_map", {}).items()
            if test_id in cpython
        }
        candidate_in_page = {
            test_id: normalize(outcome)
            for test_id, outcome in candidate_dualrun.get("pyscript_map", {}).items()
            if test_id in cpython
        }
        diff.dualrun = diff_probe_reports(pinned_in_page, candidate_in_page)
    return diff


def write_sweep_artifact(diff: SweepDiff, artifacts_dir: Path) -> Path:
    """Persist the sweep diff as ``browser-version-sweep.json``.

    Args:
        diff: Assembled sweep diff.
        artifacts_dir: Destination directory (created when missing).

    Returns:
        The path of the written artifact.

    """
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / SWEEP_ARTIFACT_NAME
    payload: dict = {
        "pinned_version": diff.pinned_version,
        "candidate_version": diff.candidate_version,
        "probes": {name: sorted(ids) for name, ids in diff.probes.items()},
        "regressions": sorted(diff.regressions),
    }
    if diff.dualrun is not None:
        payload["dualrun"] = {name: sorted(ids) for name, ids in diff.dualrun.items()}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    """CLI entry comparing two outcome reports and writing the sweep artifact.

    Exits nonzero when any probe regressed (passed at the pinned version but
    failed at the candidate), signaling the CI job to fail.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code: 0 on no regression, 1 on regression or error.

    Raises:
        ValueError: When a report file lacks the ``outcomes`` mapping
            (reported as a usage error, not propagated to the caller).

    """
    parser = argparse.ArgumentParser(
        prog="webcompy-cli._version_sweep",
        description="Diff probe outcomes across two PyScript versions.",
    )
    parser.add_argument("pinned_report", type=Path, help="Outcome JSON from the pinned-version run")
    parser.add_argument("candidate_report", type=Path, help="Outcome JSON from the candidate-version run")
    parser.add_argument("--pinned-version", default="pinned", help="Label of the pinned version")
    parser.add_argument("--candidate-version", required=True, help="Label of the candidate version")
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"))
    args = parser.parse_args(argv)

    try:
        pinned = json.loads(args.pinned_report.read_text(encoding="utf-8"))
        candidate = json.loads(args.candidate_report.read_text(encoding="utf-8"))
        if not isinstance(pinned.get("outcomes"), dict) or not isinstance(candidate.get("outcomes"), dict):
            raise ValueError("report is missing the 'outcomes' mapping")
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"error reading reports: {e}", file=sys.stderr)
        return 1

    diff = build_sweep_diff(
        args.pinned_version,
        args.candidate_version,
        pinned,
        candidate,
    )
    artifact = write_sweep_artifact(diff, args.artifacts_dir)
    print(f"sweep artifact: {artifact}")
    for name in PROBE_BUCKETS:
        print(f"{name}: {len(diff.probes[name])}")
    if diff.regressions:
        print(f"REGRESSION: {len(diff.regressions)} probe(s) failed at the candidate version:", file=sys.stderr)
        for probe_id in diff.regressions:
            print(f"  - {probe_id}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
