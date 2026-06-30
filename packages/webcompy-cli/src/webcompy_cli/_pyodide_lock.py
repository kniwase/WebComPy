from __future__ import annotations

import json
import pathlib
import urllib.error
import urllib.request

PYODIDE_LOCK_URL_TEMPLATE = "https://cdn.jsdelivr.net/pyodide/v{version}/full/pyodide-lock.json"
PYSCRIPT_RELEASE_URL_TEMPLATE = "https://pyscript.net/releases/{pyscript_version}/{filename}"
PYODIDE_RUNTIME_URL_TEMPLATE = "https://cdn.jsdelivr.net/pyodide/v{pyodide_version}/full/{filename}"

PYSCRIPT_TO_PYODIDE: dict[str, str] = {
    "2026.3.1": "0.29.3",
}


class PyodideLockFetchError(Exception):
    pass


def get_pyodide_version(pyscript_version: str) -> str:
    if pyscript_version not in PYSCRIPT_TO_PYODIDE:
        raise ValueError(
            f"Unknown PyScript version '{pyscript_version}'. "
            f"Known versions: {', '.join(sorted(PYSCRIPT_TO_PYODIDE))}. "
            f"Update the PYSCRIPT_TO_PYODIDE mapping in webcompy/cli/_pyodide_lock.py."
        )
    return PYSCRIPT_TO_PYODIDE[pyscript_version]


def _load_cached(cached_path: pathlib.Path) -> dict | None:
    if not cached_path.is_file():
        return None
    try:
        return json.loads(cached_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def fetch_pyodide_lock(pyodide_version: str, modules_dir: pathlib.Path) -> dict:
    cache_dir = modules_dir / "pyodide-lock"
    cached_path = cache_dir / f"pyodide-lock-{pyodide_version}.json"

    cached = _load_cached(cached_path)
    if cached is not None:
        return cached

    url = PYODIDE_LOCK_URL_TEMPLATE.format(version=pyodide_version)
    fetch_error: Exception | None = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WebComPy/0.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        lock_data = json.loads(data)
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError) as e:
        fetch_error = e
        lock_data = None

    if lock_data is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached_path.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")
        return lock_data

    if fetch_error is not None:
        raise PyodideLockFetchError(
            f"Failed to fetch Pyodide lock for version {pyodide_version}: {fetch_error}. "
            f"Ensure you have network access, or run 'webcompy lock' in an environment with internet access."
        )
    raise PyodideLockFetchError(
        f"Failed to parse Pyodide lock for version {pyodide_version}. The CDN may have returned invalid data."
    )
