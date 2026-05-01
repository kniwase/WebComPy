from __future__ import annotations

import hashlib
import json
import pathlib
from unittest.mock import patch

import pytest

from webcompy.cli._runtime_downloader import (
    PYODIDE_RUNTIME_ASSETS,
    PYSCRIPT_CORE_ASSETS,
    RuntimeDownloadError,
    download_runtime_assets,
)


class TestAssetLists:
    def test_pyscript_core_assets(self):
        assert "core.js" in PYSCRIPT_CORE_ASSETS
        assert "core.css" in PYSCRIPT_CORE_ASSETS

    def test_pyodide_runtime_assets(self):
        assert "pyodide.mjs" in PYODIDE_RUNTIME_ASSETS
        assert "pyodide.asm.wasm" in PYODIDE_RUNTIME_ASSETS
        assert "pyodide.asm.js" in PYODIDE_RUNTIME_ASSETS
        assert "python_stdlib.zip" in PYODIDE_RUNTIME_ASSETS
        assert "pyodide-lock.json" in PYODIDE_RUNTIME_ASSETS


FAKE_PYSCRIPT_DATA = b"pyscript-asset"
FAKE_PYODIDE_MJS_DATA = b"pyodide-mjs-data"
FAKE_PYODIDE_ASM_WASM_DATA = b"pyodide-asm-wasm-data"
FAKE_PYODIDE_ASM_JS_DATA = b"pyodide-asm-js-data"
FAKE_PYODIDE_STDLIB_DATA = b"python-stdlib-data"


def _make_fake_pyodide_lock() -> dict:
    return {
        "packages": {
            "pyodide": {
                "file_name": "pyodide.mjs",
                "sha256": hashlib.sha256(FAKE_PYODIDE_MJS_DATA).hexdigest(),
            },
            "pyodide_asm": {
                "file_name": "pyodide.asm.wasm",
                "sha256": hashlib.sha256(FAKE_PYODIDE_ASM_WASM_DATA).hexdigest(),
            },
            "python_stdlib": {
                "file_name": "python_stdlib.zip",
                "sha256": hashlib.sha256(FAKE_PYODIDE_STDLIB_DATA).hexdigest(),
            },
        },
    }


def _pyodide_data_for_url(url: str) -> bytes:
    if "pyodide-lock.json" in url:
        return json.dumps(_make_fake_pyodide_lock()).encode("utf-8")
    if "pyodide.mjs" in url:
        return FAKE_PYODIDE_MJS_DATA
    if "pyodide.asm.wasm" in url:
        return FAKE_PYODIDE_ASM_WASM_DATA
    if "pyodide.asm.js" in url:
        return FAKE_PYODIDE_ASM_JS_DATA
    if "python_stdlib.zip" in url:
        return FAKE_PYODIDE_STDLIB_DATA
    return b"unknown-pyodide-asset"


def _mock_download_file(url: str, dest: pathlib.Path) -> bytes:
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = FAKE_PYSCRIPT_DATA if "pyscript.net" in url else _pyodide_data_for_url(url)
    dest.write_bytes(data)
    return data


@pytest.fixture
def clean_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache" / "webcompy" / "runtime-assets"
    monkeypatch.setattr("webcompy.cli._runtime_downloader.CACHE_DIR", cache_dir)
    yield cache_dir


class TestDownloadRuntimeAssets:
    def test_downloads_all_assets_to_correct_dirs(self, tmp_path, clean_cache):
        pyodide_version = "0.29.3"
        pyscript_version = "2026.3.1"

        with patch("webcompy.cli._runtime_downloader._download_file", side_effect=_mock_download_file):
            dest_dir = tmp_path / "assets"
            dest_dir.mkdir()
            download_runtime_assets(pyodide_version, pyscript_version, dest_dir)

        assert (dest_dir / "core.js").is_file()
        assert (dest_dir / "core.css").is_file()
        assert (dest_dir / "pyodide" / "pyodide.mjs").is_file()
        assert (dest_dir / "pyodide" / "pyodide.asm.wasm").is_file()
        assert (dest_dir / "pyodide" / "pyodide.asm.js").is_file()
        assert (dest_dir / "pyodide" / "python_stdlib.zip").is_file()
        assert (dest_dir / "pyodide" / "pyodide-lock.json").is_file()

    def test_caches_assets(self, tmp_path, clean_cache):
        pyodide_version = "0.29.3"
        pyscript_version = "2026.3.1"
        download_counts = {"total": 0}

        def counting_mock(url, dest):
            download_counts["total"] += 1
            return _mock_download_file(url, dest)

        with patch("webcompy.cli._runtime_downloader._download_file", side_effect=counting_mock):
            dest1 = tmp_path / "dest1"
            dest1.mkdir()
            download_runtime_assets(pyodide_version, pyscript_version, dest1)
            first_count = download_counts["total"]

        with patch("webcompy.cli._runtime_downloader._download_file", side_effect=counting_mock):
            dest2 = tmp_path / "dest2"
            dest2.mkdir()
            download_runtime_assets(pyodide_version, pyscript_version, dest2)
            second_count = download_counts["total"] - first_count

        assert second_count == 0

    def test_sha256_mismatch_raises_error(self, tmp_path, clean_cache):
        pyodide_version = "0.29.3"
        pyscript_version = "2026.3.1"

        def mismatch_mock(url, dest):
            if "pyscript.net" in url:
                return _mock_download_file(url, dest)
            data = _pyodide_data_for_url(url)
            if "pyodide-lock.json" not in url:
                data = b"corrupted-data"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return data

        with patch("webcompy.cli._runtime_downloader._download_file", side_effect=mismatch_mock):
            dest_dir = tmp_path / "assets"
            dest_dir.mkdir()
            with pytest.raises(RuntimeDownloadError):
                download_runtime_assets(pyodide_version, pyscript_version, dest_dir)

    def test_download_failure_raises_error(self, tmp_path, clean_cache):
        pyodide_version = "0.29.3"
        pyscript_version = "2026.3.1"

        with patch(
            "webcompy.cli._runtime_downloader._download_file",
            side_effect=RuntimeDownloadError("Failed to download: network error"),
        ):
            dest_dir = tmp_path / "assets"
            dest_dir.mkdir()
            with pytest.raises(RuntimeDownloadError):
                download_runtime_assets(pyodide_version, pyscript_version, dest_dir)
