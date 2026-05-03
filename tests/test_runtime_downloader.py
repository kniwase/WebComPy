from __future__ import annotations

import hashlib
import io
import pathlib
import zipfile
from unittest.mock import patch

import pytest

from webcompy.cli._runtime_downloader import (
    PYODIDE_RUNTIME_ASSETS,
    RuntimeDownloadError,
    download_pyscript_bundle,
    download_runtime_assets,
)

FAKE_PYODIDE_DATA_MAP: dict[str, bytes] = {
    "pyodide-lock.json": b"pyodide-lock-data",
    "pyodide.mjs": b"pyodide-mjs-data",
    "pyodide.asm.wasm": b"pyodide-asm-wasm-data",
    "pyodide.asm.js": b"pyodide-asm-js-data",
    "python_stdlib.zip": b"python-stdlib-data",
}

FAKE_BUNDLE_FILES: dict[str, bytes] = {
    "core.js": b"core-entry",
    "core.css": b"core-style",
    "core-BuLtL7jM.js": b"core-bundle",
    "donkey-2hW3ZLW0.js": b"donkey",
    "py-terminal-ggn9CTLw.js": b"py-terminal",
}
EXCLUDED_IN_ZIP: dict[str, bytes] = {
    "core.js.map": b"map-content",
    "xterm.d.ts": b"type-def",
    "micropython/micropython.mjs": b"micropython",
    "pyodide/pyodide.mjs": b"nested-pyodide",
    "service-worker.js": b"sw",
    "mini-coi-fd.js": b"coi",
    "xterm.css": b"xterm-css",
    "index.html": b"html",
}


def _create_fake_bundle_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in {**FAKE_BUNDLE_FILES, **EXCLUDED_IN_ZIP}.items():
            zf.writestr(f"pyscript/{name}", content)
        zf.writestr("pyscript/micropython/", "")
        zf.writestr("pyscript/pyodide/", "")
    return buf.getvalue()


def _make_bundle_and_pyodide_mock():
    def mock(url: str, dest: pathlib.Path) -> bytes:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if "offline_" in url:
            data = _create_fake_bundle_zip()
        else:
            filename = url.rsplit("/", 1)[-1]
            data = FAKE_PYODIDE_DATA_MAP.get(filename, b"unknown")
        dest.write_bytes(data)
        return data

    return mock


class TestPyodideAssetLists:
    def test_pyodide_runtime_assets(self):
        assert "pyodide.mjs" in PYODIDE_RUNTIME_ASSETS
        assert "pyodide.asm.wasm" in PYODIDE_RUNTIME_ASSETS
        assert "pyodide.asm.js" in PYODIDE_RUNTIME_ASSETS
        assert "python_stdlib.zip" in PYODIDE_RUNTIME_ASSETS
        assert "pyodide-lock.json" in PYODIDE_RUNTIME_ASSETS


class TestDownloadPyscriptBundle:
    def test_downloads_and_extracts_only_js_and_css(self, tmp_path):
        modules_dir = tmp_path / ".webcompy_modules"

        with patch(
            "webcompy.cli._runtime_downloader._download_file",
            side_effect=_make_bundle_and_pyodide_mock(),
        ):
            results = download_pyscript_bundle("2026.3.1", modules_dir)

        for name in FAKE_BUNDLE_FILES:
            assert name in results, f"Expected {name} in results"
        for name in EXCLUDED_IN_ZIP:
            assert name not in results, f"Should not have {name} in results"

        cache_dir = modules_dir / "runtime-assets" / "2026.3.1" / "pyscript"
        for name in FAKE_BUNDLE_FILES:
            assert (cache_dir / name).is_file(), f"Expected {name} cached"
        for name in EXCLUDED_IN_ZIP:
            assert not (cache_dir / name).is_file(), f"Should not cache {name}"

    def test_returns_sha256_hashes(self, tmp_path):
        modules_dir = tmp_path / ".webcompy_modules"

        with patch(
            "webcompy.cli._runtime_downloader._download_file",
            side_effect=_make_bundle_and_pyodide_mock(),
        ):
            results = download_pyscript_bundle("2026.3.1", modules_dir)

        for _filename, (path, sha256) in results.items():
            assert isinstance(sha256, str)
            assert len(sha256) == 64
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            assert sha256 == expected

    def test_caches_bundle_on_second_call(self, tmp_path):
        modules_dir = tmp_path / ".webcompy_modules"
        download_counts = {"total": 0}

        def counting_mock(url, dest):
            download_counts["total"] += 1
            return _make_bundle_and_pyodide_mock()(url, dest)

        with patch("webcompy.cli._runtime_downloader._download_file", side_effect=counting_mock):
            download_pyscript_bundle("2026.3.1", modules_dir)
            first_count = download_counts["total"]

        with patch("webcompy.cli._runtime_downloader._download_file", side_effect=counting_mock):
            download_pyscript_bundle("2026.3.1", modules_dir)
            second_count = download_counts["total"] - first_count

        assert second_count == 0

    def test_clears_zip_after_extraction(self, tmp_path):
        modules_dir = tmp_path / ".webcompy_modules"

        with patch(
            "webcompy.cli._runtime_downloader._download_file",
            side_effect=_make_bundle_and_pyodide_mock(),
        ):
            download_pyscript_bundle("2026.3.1", modules_dir)

        cache_dir = modules_dir / "runtime-assets" / "2026.3.1" / "pyscript"
        assert not (cache_dir / "offline.zip").is_file()


class TestDownloadRuntimeAssets:
    def test_combines_bundle_with_pyodide_assets(self, tmp_path):
        pyodide_version = "0.29.3"
        pyscript_version = "2026.3.1"
        modules_dir = tmp_path / ".webcompy_modules"

        with patch(
            "webcompy.cli._runtime_downloader._download_file",
            side_effect=_make_bundle_and_pyodide_mock(),
        ):
            results = download_runtime_assets(pyodide_version, pyscript_version, modules_dir)

        for name in FAKE_BUNDLE_FILES:
            assert name in results
        assert "pyodide/pyodide.mjs" in results
        assert "pyodide/pyodide.asm.wasm" in results
        assert "pyodide/pyodide.asm.js" in results
        assert "pyodide/python_stdlib.zip" in results
        assert "pyodide/pyodide-lock.json" in results

    def test_copies_to_dest_dir(self, tmp_path):
        pyodide_version = "0.29.3"
        pyscript_version = "2026.3.1"
        modules_dir = tmp_path / ".webcompy_modules"
        dest_dir = tmp_path / "output"

        with patch(
            "webcompy.cli._runtime_downloader._download_file",
            side_effect=_make_bundle_and_pyodide_mock(),
        ):
            results = download_runtime_assets(pyodide_version, pyscript_version, modules_dir, dest_dir)

        assert (dest_dir / "core.js").is_file()
        assert (dest_dir / "core-BuLtL7jM.js").is_file()
        assert (dest_dir / "pyodide" / "pyodide.mjs").is_file()
        for name in FAKE_BUNDLE_FILES:
            assert name in results
            assert results[name][0] == dest_dir / name

    def test_pyodide_assets_cached(self, tmp_path):
        pyodide_version = "0.29.3"
        pyscript_version = "2026.3.1"
        modules_dir = tmp_path / ".webcompy_modules"
        download_counts = {"total": 0}

        def counting_mock(url, dest):
            download_counts["total"] += 1
            return _make_bundle_and_pyodide_mock()(url, dest)

        with patch("webcompy.cli._runtime_downloader._download_file", side_effect=counting_mock):
            download_runtime_assets(pyodide_version, pyscript_version, modules_dir)
            first_count = download_counts["total"]

        with patch("webcompy.cli._runtime_downloader._download_file", side_effect=counting_mock):
            download_runtime_assets(pyodide_version, pyscript_version, modules_dir)
            second_count = download_counts["total"] - first_count

        assert second_count == 0

    def test_sha256_for_all_assets(self, tmp_path):
        pyodide_version = "0.29.3"
        pyscript_version = "2026.3.1"
        modules_dir = tmp_path / ".webcompy_modules"

        with patch(
            "webcompy.cli._runtime_downloader._download_file",
            side_effect=_make_bundle_and_pyodide_mock(),
        ):
            results = download_runtime_assets(pyodide_version, pyscript_version, modules_dir)

        for _filename, (path, sha256) in results.items():
            assert isinstance(sha256, str)
            assert len(sha256) == 64
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            assert sha256 == expected

    def test_download_failure_raises_error(self, tmp_path):
        pyodide_version = "0.29.3"
        pyscript_version = "2026.3.1"
        modules_dir = tmp_path / ".webcompy_modules"

        with (
            patch(
                "webcompy.cli._runtime_downloader._download_file",
                side_effect=RuntimeDownloadError("Failed to download: network error"),
            ),
            pytest.raises(RuntimeDownloadError),
        ):
            download_runtime_assets(pyodide_version, pyscript_version, modules_dir)
