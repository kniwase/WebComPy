from __future__ import annotations

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    if os.environ.get("WEBCOMPY_RUN_E2E") != "1":
        raise pytest.UsageError(
            "E2E tests are gated by the WEBCOMPY_RUN_E2E=1 environment variable. "
            "Run via scripts/run-e2e-tests.sh, or for advanced direct invocation: "
            "WEBCOMPY_RUN_E2E=1 uv run pytest e2e/..."
        )
