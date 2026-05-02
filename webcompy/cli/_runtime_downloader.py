from __future__ import annotations

import hashlib
import os
import pathlib
import urllib.error
import urllib.request

from webcompy.cli._pyodide_lock import PYODIDE_RUNTIME_URL_TEMPLATE, PYSCRIPT_RELEASE_URL_TEMPLATE

PYSCRIPT_CORE_ASSETS = ["core.js", "core.css"]
PYODIDE_RUNTIME_ASSETS = [
    "pyodide.mjs",
    "pyodide.asm.wasm",
    "pyodide.asm.js",
    "python_stdlib.zip",
    "pyodide-lock.json",
]

CACHE_DIR = (
    pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache")) / "webcompy" / "runtime-assets"
)


class RuntimeDownloadError(Exception):
    pass


def _sha256_of_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _download_file(url: str, dest: pathlib.Path) -> bytes:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise RuntimeDownloadError(f"Failed to download {url}: {e}. Ensure you have network access.") from e
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return data


def download_runtime_assets(
    pyodide_version: str,
    pyscript_version: str,
    dest_dir: pathlib.Path,
) -> dict[str, tuple[pathlib.Path, str]]:
    results: dict[str, tuple[pathlib.Path, str]] = {}
    cache_dir = CACHE_DIR / pyscript_version

    for filename in PYSCRIPT_CORE_ASSETS:
        cached_path = cache_dir / filename
        dest_path = dest_dir / filename
        rel_path = filename

        if cached_path.is_file():
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(cached_path.read_bytes())
            sha256 = _sha256_of_file(dest_path)
            results[rel_path] = (dest_path, sha256)
            continue

        url = PYSCRIPT_RELEASE_URL_TEMPLATE.format(pyscript_version=pyscript_version, filename=filename)
        data = _download_file(url, cached_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        sha256 = hashlib.sha256(data).hexdigest()
        results[rel_path] = (dest_path, sha256)

    pyodide_dest_dir = dest_dir / "pyodide"
    pyodide_cache_dir = cache_dir / "pyodide"

    for filename in PYODIDE_RUNTIME_ASSETS:
        cached_path = pyodide_cache_dir / filename
        dest_path = pyodide_dest_dir / filename
        rel_path = f"pyodide/{filename}"

        if cached_path.is_file():
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(cached_path.read_bytes())
            sha256 = _sha256_of_file(dest_path)
            results[rel_path] = (dest_path, sha256)
            continue

        url = PYODIDE_RUNTIME_URL_TEMPLATE.format(pyodide_version=pyodide_version, filename=filename)
        data = _download_file(url, cached_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        sha256 = hashlib.sha256(data).hexdigest()
        results[rel_path] = (dest_path, sha256)

    return results
