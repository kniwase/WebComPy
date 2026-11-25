from __future__ import annotations

import os
import re

import pytest

_INVALID_ARTIFACT_CHARS_RE = re.compile(r'[\\/:*?"<>|\r\n ]')


def sanitize_console_log_name(name: str) -> str:
    return _INVALID_ARTIFACT_CHARS_RE.sub("_", name.replace("::", "__"))


def pytest_configure(config: pytest.Config) -> None:
    if os.environ.get("WEBCOMPY_RUN_E2E") != "1":
        raise pytest.UsageError(
            "E2E tests must be run via scripts/run-e2e-tests.sh\n"
            "Example: scripts/run-e2e-tests.sh components --serving-mode=static\n"
            "To run a single file: scripts/run-e2e-tests.sh --file e2e/core/test_overlay.py --serving-mode=static\n"
            "See scripts/run-e2e-tests.sh --help for details."
        )
