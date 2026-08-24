"""Discovery-gating behavior of the browser test tier.

The tier must never be part of default pytest discovery — even when
``WEBCOMPY_RUN_BROWSER=1`` is set — unless a path argument explicitly selects
``tests/browser/**``.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.conftest import _invocation_targets_browser_tier, pytest_ignore_collect

REPO_ROOT = Path(__file__).resolve().parent.parent
BROWSER_DIR = REPO_ROOT / "tests" / "browser"


class TestInvocationTargeting:
    @pytest.mark.parametrize(
        ("arg", "expected"),
        [
            ("tests/browser", True),
            ("tests/browser/", True),
            ("tests/browser/test_signal_browser.py", True),
            ("tests/browser/test_signal_browser.py::test_x", True),
            ("tests/", False),
            ("tests/test_signal.py", False),
            ("-k", False),
        ],
    )
    def test_targeting(self, arg, expected):
        assert _invocation_targets_browser_tier([arg]) is expected


def _ignore(path: Path, args: list[str]) -> bool | None:
    return pytest_ignore_collect(path, SimpleNamespace(args=args))


class TestIgnoreCollectDecision:
    def test_ignores_browser_directory_when_not_targeted(self):
        assert _ignore(BROWSER_DIR, []) is True

    def test_ignores_browser_file_when_not_targeted(self):
        assert _ignore(BROWSER_DIR / "test_signal_browser.py", ["tests"]) is True

    def test_allows_when_targeted_by_directory(self):
        assert _ignore(BROWSER_DIR / "test_signal_browser.py", ["tests/browser"]) is None

    def test_allows_when_targeted_by_node_id(self):
        assert _ignore(BROWSER_DIR / "test_signal_browser.py", ["tests/browser/test_signal_browser.py::test_x"]) is None

    def test_paths_outside_tests_dir_are_untouched(self, tmp_path):
        assert _ignore(tmp_path / "elsewhere" / "test_a.py", []) is None


def _collect_browser_item_count(env: dict[str, str]) -> tuple[int, str]:
    process_env = os.environ.copy()
    process_env.pop("WEBCOMPY_RUN_BROWSER", None)
    process_env.update(env)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=process_env,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    collected = re.findall(r"^tests/browser/\S+::", result.stdout, re.MULTILINE)
    return len(collected), "\n".join(collected)


def test_default_discovery_excludes_browser_tier_without_gate():
    count, output = _collect_browser_item_count({})
    assert count == 0, output[-2000:]


def test_gated_default_discovery_still_excludes_browser_tier():
    count, output = _collect_browser_item_count({"WEBCOMPY_RUN_BROWSER": "1"})
    assert count == 0, output[-2000:]
