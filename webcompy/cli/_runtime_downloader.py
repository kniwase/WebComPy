from __future__ import annotations

import hashlib
import json
import os
import pathlib
import urllib.error
import urllib.request

PYSCRIPT_RELEASE_URL_TEMPLATE = "https://pyscript.net/releases/{pyscript_version}/{filename}"
PYODIDE_RUNTIME_URL_TEMPLATE = "https://cdn.jsdelivr.net/pyodide/v{pyodide_version}/full/{filename}"

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


def _get_pyodide_runtime_hashes(pyodide_lock_path: pathlib.Path) -> dict[str, str]:
    try:
        lock_data = json.loads(pyodide_lock_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise RuntimeDownloadError(f"Failed to parse pyodide-lock.json for runtime hashes: {e}") from e
    packages = lock_data.get("packages", {})
    hashes: dict[str, str] = {}
    for name in ("pyodide", "pyodide_asm", "python_stdlib"):
        pkg = packages.get(name, {})
        if isinstance(pkg, dict) and "sha256" in pkg:
            hashes[pkg.get("file_name", "")] = pkg["sha256"]
    return hashes


def download_runtime_assets(
    pyodide_version: str,
    pyscript_version: str,
    dest_dir: pathlib.Path,
) -> dict[str, pathlib.Path]:
    results: dict[str, pathlib.Path] = {}
    cache_dir = CACHE_DIR / pyscript_version

    for filename in PYSCRIPT_CORE_ASSETS:
        cached_path = cache_dir / filename
        dest_path = dest_dir / filename

        if cached_path.is_file():
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(cached_path.read_bytes())
            results[filename] = dest_path
            continue

        url = PYSCRIPT_RELEASE_URL_TEMPLATE.format(pyscript_version=pyscript_version, filename=filename)
        data = _download_file(url, cached_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        results[filename] = dest_path

    pyodide_dest_dir = dest_dir / "pyodide"
    pyodide_cache_dir = cache_dir / "pyodide"
    pyodide_lock_path: pathlib.Path | None = None

    for filename in PYODIDE_RUNTIME_ASSETS:
        cached_path = pyodide_cache_dir / filename
        dest_path = pyodide_dest_dir / filename

        if cached_path.is_file():
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(cached_path.read_bytes())
            results[filename] = dest_path
            if filename == "pyodide-lock.json":
                pyodide_lock_path = cached_path
            continue

        url = PYODIDE_RUNTIME_URL_TEMPLATE.format(pyodide_version=pyodide_version, filename=filename)
        data = _download_file(url, cached_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        results[filename] = dest_path
        if filename == "pyodide-lock.json":
            pyodide_lock_path = cached_path

    if pyodide_lock_path is not None:
        runtime_hashes = _get_pyodide_runtime_hashes(pyodide_lock_path)
        for filename, expected_sha256 in runtime_hashes.items():
            cached_path = pyodide_cache_dir / filename
            if not cached_path.is_file():
                continue
            actual_sha256 = _sha256_of_file(cached_path)
            if actual_sha256 != expected_sha256:
                cached_path.unlink()
                raise RuntimeDownloadError(
                    f"SHA256 verification failed for {filename}. "
                    f"Expected: {expected_sha256}, got: {actual_sha256}. "
                    f"The download may be corrupted. Delete the cache and try again."
                )

    return results
