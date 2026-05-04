from __future__ import annotations

import hashlib
import pathlib
import urllib.error
import urllib.request
import zipfile

from webcompy.cli._pyodide_lock import PYODIDE_RUNTIME_URL_TEMPLATE

PYSCRIPT_OFFLINE_URL_TEMPLATE = "https://pyscript.net/releases/{pyscript_version}/offline_{pyscript_version}.zip"
PYODIDE_RUNTIME_ASSETS = [
    "pyodide.mjs",
    "pyodide.asm.wasm",
    "pyodide.asm.js",
    "python_stdlib.zip",
    "pyodide-lock.json",
]

_EXCLUDED_ZIP_NAMES = frozenset(
    {
        "micropython",
        "pyodide",
        "service-worker.js",
        "mini-coi-fd.js",
        "xterm.css",
        "index.html",
    }
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
        req = urllib.request.Request(url, headers={"User-Agent": "WebComPy/0.1"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise RuntimeDownloadError(f"Failed to download {url}: {e}. Ensure you have network access.") from e
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return data


def _should_extract(member_name: str) -> bool:
    parts = member_name.split("/")
    if len(parts) < 3:
        return False
    if parts[0] != "offline" or parts[1] != "pyscript":
        return False
    filename = parts[2]
    if not filename:
        return False
    if filename.endswith(".map") or filename.endswith(".d.ts"):
        return False
    if filename in _EXCLUDED_ZIP_NAMES:
        return False
    return filename.endswith(".js") or filename.endswith(".css")


def download_pyscript_bundle(
    pyscript_version: str,
    modules_dir: pathlib.Path,
) -> dict[str, tuple[pathlib.Path, str]]:
    cache_dir = modules_dir / "runtime-assets" / pyscript_version / "pyscript"
    cache_dir.mkdir(parents=True, exist_ok=True)

    existing_files = list(cache_dir.glob("*.js")) + list(cache_dir.glob("*.css"))
    has_full_bundle = any(f.name not in ("core.js", "core.css") for f in existing_files)
    if has_full_bundle:
        results: dict[str, tuple[pathlib.Path, str]] = {}
        for f in existing_files:
            if f.name.endswith(".map") or f.name.endswith(".d.ts"):
                continue
            results[f.name] = (f, _sha256_of_file(f))
        return results

    url = PYSCRIPT_OFFLINE_URL_TEMPLATE.format(pyscript_version=pyscript_version)
    _download_file(url, cache_dir / "offline.zip")
    zip_path = cache_dir / "offline.zip"

    results = {}
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if not _should_extract(info.filename):
                continue
            target_path = cache_dir / pathlib.Path(info.filename).name
            with zf.open(info) as src:
                data = src.read()
            target_path.write_bytes(data)
            sha256 = hashlib.sha256(data).hexdigest()
            results[target_path.name] = (target_path, sha256)

    zip_path.unlink()
    return results


def _get_cdn_package_files(lockfile) -> list[tuple[str, str]]:
    if lockfile is None:
        return []
    result: list[tuple[str, str]] = []
    for entry in lockfile.pure_python_packages.values():
        if entry.in_pyodide_cdn and entry.pyodide_file_name and entry.pyodide_sha256:
            result.append((entry.pyodide_file_name, entry.pyodide_sha256))
    return result


def download_runtime_assets(
    pyodide_version: str,
    pyscript_version: str,
    modules_dir: pathlib.Path,
    dest_dir: pathlib.Path | None = None,
    lock_file: object = None,
) -> dict[str, tuple[pathlib.Path, str]]:
    from webcompy.cli._lockfile import Lockfile

    results = download_pyscript_bundle(pyscript_version, modules_dir)

    if dest_dir is not None:
        copied: dict[str, tuple[pathlib.Path, str]] = {}
        for filename, (src_path, sha256) in results.items():
            dest_path = dest_dir / filename
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if dest_path != src_path:
                dest_path.write_bytes(src_path.read_bytes())
            copied[filename] = (dest_path, sha256)
        results = copied

    pyodide_dest_dir = (dest_dir or modules_dir / "runtime-assets" / pyscript_version) / "pyodide"
    pyodide_cache_dir = modules_dir / "runtime-assets" / pyscript_version / "pyodide"

    for filename in PYODIDE_RUNTIME_ASSETS:
        cached_path = pyodide_cache_dir / filename
        dest_path = pyodide_dest_dir / filename
        rel_path = f"pyodide/{filename}"

        if cached_path.is_file():
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if dest_path != cached_path:
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

    if isinstance(lock_file, Lockfile):
        from webcompy.cli._pyodide_downloader import download_pyodide_wheel
        from webcompy.cli._pyodide_lock import fetch_pyodide_lock

        pyodide_lock = fetch_pyodide_lock(pyodide_version, modules_dir)
        micropip_info = pyodide_lock.get("packages", {}).get("micropip", {})
        cdn_files = _get_cdn_package_files(lock_file)
        extra_files: list[tuple[str, str]] = []
        if micropip_info.get("file_name") and micropip_info.get("sha256"):
            extra_files.append((micropip_info["file_name"], micropip_info["sha256"]))
        for file_name, sha256_val in cdn_files + extra_files:
            try:
                wheel_path = download_pyodide_wheel(file_name, pyodide_version, sha256_val, modules_dir)
            except Exception:
                continue
            dest_path = pyodide_dest_dir / file_name
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if dest_path != wheel_path:
                dest_path.write_bytes(wheel_path.read_bytes())
            sha256 = _sha256_of_file(dest_path)
            results[f"pyodide/{file_name}"] = (dest_path, sha256)

    return results
