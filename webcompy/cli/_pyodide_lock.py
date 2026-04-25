from __future__ import annotations

import json
import os
import pathlib
import urllib.error
import urllib.request

PYODIDE_LOCK_URL_TEMPLATE = "https://cdn.jsdelivr.net/pyodide/v{version}/full/pyodide-lock.json"

CACHE_DIR = pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache")) / "webcompy"

PYSCRIPT_TO_PYODIDE: dict[str, str] = {
    "2026.3.1": "0.29.3",
}


def get_pyodide_version(pyscript_version: str) -> str:
    if pyscript_version not in PYSCRIPT_TO_PYODIDE:
        raise ValueError(
            f"Unknown PyScript version '{pyscript_version}'. "
            f"Known versions: {', '.join(sorted(PYSCRIPT_TO_PYODIDE))}. "
            f"Update the PYSCRIPT_TO_PYODIDE mapping in webcompy/cli/_pyodide_lock.py."
        )
    return PYSCRIPT_TO_PYODIDE[pyscript_version]


def fetch_pyodide_lock(pyodide_version: str) -> dict | None:
    cached_path = CACHE_DIR / f"pyodide-lock-{pyodide_version}.json"

    if cached_path.is_file():
        try:
            return json.loads(cached_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    url = PYODIDE_LOCK_URL_TEMPLATE.format(version=pyodide_version)
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        lock_data = json.loads(data)
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
        if cached_path.is_file():
            try:
                return json.loads(cached_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached_path.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")
    return lock_data
