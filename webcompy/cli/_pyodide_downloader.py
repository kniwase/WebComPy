from __future__ import annotations

import hashlib
import os
import pathlib
import urllib.error
import urllib.request
import zipfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webcompy.cli._lockfile import Lockfile

PYODIDE_CDN_URL_TEMPLATE = "https://cdn.jsdelivr.net/pyodide/v{version}/full/{file_name}"

CACHE_DIR = (
    pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache")) / "webcompy" / "pyodide-packages"
)


class PyodideDownloadError(Exception):
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


def download_pyodide_wheel(
    file_name: str,
    pyodide_version: str,
    expected_sha256: str,
) -> pathlib.Path:
    cache_dir = CACHE_DIR / pyodide_version
    cached_path = cache_dir / file_name

    if cached_path.is_file():
        actual_sha256 = _sha256_of_file(cached_path)
        if actual_sha256 == expected_sha256:
            return cached_path
        cached_path.unlink()

    url = PYODIDE_CDN_URL_TEMPLATE.format(version=pyodide_version, file_name=file_name)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WebComPy"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise PyodideDownloadError(
            f"Failed to download {file_name} from Pyodide CDN: {e}. Ensure you have network access."
        ) from e

    actual_sha256 = hashlib.sha256(data).hexdigest()
    if actual_sha256 != expected_sha256:
        raise PyodideDownloadError(
            f"SHA256 verification failed for {file_name}. "
            f"Expected: {expected_sha256}, got: {actual_sha256}. "
            f"The download may be corrupted or the lock file may be outdated."
        )

    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_path.write_bytes(data)
    return cached_path


def download_wasm_wheels(
    lockfile: Lockfile,
) -> dict[str, pathlib.Path]:
    results: dict[str, pathlib.Path] = {}
    for name, entry in lockfile.wasm_packages.items():
        if entry.file_name and entry.sha256:
            wheel_path = download_pyodide_wheel(
                entry.file_name,
                lockfile.pyodide_version,
                entry.sha256,
            )
            results[name] = wheel_path
    return results


def extract_wheel(
    wheel_path: pathlib.Path,
    dest: pathlib.Path,
) -> list[tuple[str, pathlib.Path]]:
    with zipfile.ZipFile(wheel_path, "r") as zf:
        zf.extractall(dest)

    result: list[tuple[str, pathlib.Path]] = []
    for dist_info in sorted(dest.glob("*.dist-info")):
        top_level_path = dist_info / "top_level.txt"
        if top_level_path.exists():
            for line in top_level_path.read_text(encoding="utf-8").strip().splitlines():
                pkg_name = line.strip()
                if pkg_name:
                    pkg_dir = dest / pkg_name
                    if pkg_dir.is_dir():
                        result.append((pkg_name, pkg_dir))
                    elif (dest / f"{pkg_name}.py").is_file():
                        result.append((pkg_name, dest))
        else:
            pkg_name = dist_info.name.split("-")[0]
            pkg_dir = dest / pkg_name
            if pkg_dir.is_dir():
                result.append((pkg_name, pkg_dir))

    return result
