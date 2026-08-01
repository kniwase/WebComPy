from __future__ import annotations

import asyncio

import pytest

import webcompy.utils._environment as env_mod
from webcompy.elements.types._dynamic import _run_refresh_sync


@pytest.mark.asyncio
async def test_pyscript_schedules_refresh_instead_of_blocking(monkeypatch):
    monkeypatch.setattr(env_mod, "ENVIRONMENT", "pyscript")
    calls: list[str] = []

    async def refresh(value: str) -> None:
        calls.append(value)

    _run_refresh_sync(refresh, "x")
    assert calls == []
    await asyncio.sleep(0)
    assert calls == ["x"]


@pytest.mark.asyncio
async def test_pyscript_logs_refresh_errors(monkeypatch):
    monkeypatch.setattr(env_mod, "ENVIRONMENT", "pyscript")
    logged: list[object] = []

    def fake_error(msg: object) -> None:
        logged.append(msg)

    monkeypatch.setattr("webcompy.logging.error", fake_error)

    async def refresh(value: str) -> None:
        raise ValueError("boom")

    _run_refresh_sync(refresh, "x")
    await asyncio.sleep(0)
    assert len(logged) == 1
    assert isinstance(logged[0], str)
    assert "Traceback (most recent call last):" in logged[0]
    assert "ValueError: boom" in logged[0]


@pytest.mark.asyncio
async def test_other_env_completes_refresh_synchronously(monkeypatch):
    monkeypatch.setattr(env_mod, "ENVIRONMENT", "other")
    calls: list[str] = []

    async def refresh(value: str) -> None:
        calls.append(value)

    _run_refresh_sync(refresh, "x")
    assert calls == ["x"]
