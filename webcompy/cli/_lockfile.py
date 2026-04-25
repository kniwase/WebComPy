from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field

from webcompy.cli._pyodide_lock import fetch_pyodide_lock, get_pyodide_version

LOCKFILE_VERSION = 1
LOCKFILE_NAME = "webcompy-lock.json"


@dataclass
class PyodidePackageEntry:
    version: str
    file_name: str
    is_wasm: bool

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "file_name": self.file_name,
            "is_wasm": self.is_wasm,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PyodidePackageEntry:
        return cls(
            version=data["version"],
            file_name=data["file_name"],
            is_wasm=data["is_wasm"],
        )


@dataclass
class BundledPackageEntry:
    version: str
    source: str
    is_pure_python: bool

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "source": self.source,
            "is_pure_python": self.is_pure_python,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BundledPackageEntry:
        return cls(
            version=data["version"],
            source=data["source"],
            is_pure_python=data["is_pure_python"],
        )


@dataclass
class Lockfile:
    pyodide_version: str
    pyscript_version: str
    pyodide_packages: dict[str, PyodidePackageEntry] = field(default_factory=dict)
    bundled_packages: dict[str, BundledPackageEntry] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "version": LOCKFILE_VERSION,
            "pyodide_version": self.pyodide_version,
            "pyscript_version": self.pyscript_version,
            "pyodide_packages": {name: entry.to_dict() for name, entry in self.pyodide_packages.items()},
            "bundled_packages": {name: entry.to_dict() for name, entry in self.bundled_packages.items()},
        }


def load_lockfile(path: pathlib.Path) -> Lockfile | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("version") != LOCKFILE_VERSION:
        return None
    pyodide_packages = {
        name: PyodidePackageEntry.from_dict(entry) for name, entry in data.get("pyodide_packages", {}).items()
    }
    bundled_packages = {
        name: BundledPackageEntry.from_dict(entry) for name, entry in data.get("bundled_packages", {}).items()
    }
    return Lockfile(
        pyodide_version=data["pyodide_version"],
        pyscript_version=data["pyscript_version"],
        pyodide_packages=pyodide_packages,
        bundled_packages=bundled_packages,
    )


def save_lockfile(lockfile: Lockfile, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(lockfile.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )


def generate_lockfile(
    dependencies: list[str],
    pyscript_version: str,
    pyodide_version: str | None = None,
) -> tuple[Lockfile, list[str]]:
    if pyodide_version is None:
        pyodide_version = get_pyodide_version(pyscript_version)

    pyodide_lock = fetch_pyodide_lock(pyodide_version)

    from webcompy.cli._dependency_resolver import classify_dependencies

    classified, errors = classify_dependencies(dependencies, pyodide_lock)

    pyodide_packages: dict[str, PyodidePackageEntry] = {}
    bundled_packages: dict[str, BundledPackageEntry] = {}

    for dep in classified:
        if dep.is_wasm:
            file_name = ""
            if pyodide_lock is not None:
                pkg_info = pyodide_lock.get("packages", {}).get(dep.name, {})
                file_name = pkg_info.get("file_name", "")
            pyodide_packages[dep.name] = PyodidePackageEntry(
                version=dep.version,
                file_name=file_name,
                is_wasm=True,
            )
        else:
            bundled_packages[dep.name] = BundledPackageEntry(
                version=dep.version,
                source=dep.source if dep.source in ("explicit", "transitive") else "transitive",
                is_pure_python=dep.is_pure_python,
            )

    lockfile = Lockfile(
        pyodide_version=pyodide_version,
        pyscript_version=pyscript_version,
        pyodide_packages=pyodide_packages,
        bundled_packages=bundled_packages,
    )

    return lockfile, errors


def validate_lockfile(
    lockfile: Lockfile,
    dependencies: list[str],
) -> list[str]:
    issues: list[str] = []
    explicit_in_lock = {name for name, entry in lockfile.bundled_packages.items() if entry.source == "explicit"}
    pyodide_names = set(lockfile.pyodide_packages.keys())
    all_explicit_in_lock = explicit_in_lock | pyodide_names
    dep_set = {d.replace("-", "_") for d in dependencies}
    lock_set = {n.replace("-", "_") for n in all_explicit_in_lock}
    missing = dep_set - lock_set
    if missing:
        issues.append(f"Dependencies missing from lock file: {', '.join(sorted(missing))}")
    extra = lock_set - dep_set
    if extra:
        issues.append(f"Extra dependencies in lock file: {', '.join(sorted(extra))}")
    return issues


def get_bundled_deps(
    lockfile: Lockfile | None,
) -> list[tuple[str, pathlib.Path]]:
    if lockfile is None:
        return []
    from webcompy.cli._dependency_resolver import _find_package_dir

    result: list[tuple[str, pathlib.Path]] = []
    seen: set[str] = set()
    for name, entry in lockfile.bundled_packages.items():
        if not entry.is_pure_python:
            continue
        norm = name.replace("-", "_")
        if norm in seen:
            continue
        seen.add(norm)
        pkg_dir = _find_package_dir(name)
        if pkg_dir is not None:
            result.append((name, pkg_dir))
    for name, entry in lockfile.pyodide_packages.items():
        if entry.is_wasm:
            continue
        norm = name.replace("-", "_")
        if norm in seen:
            continue
        seen.add(norm)
        pkg_dir = _find_package_dir(name)
        if pkg_dir is not None:
            result.append((name, pkg_dir))
    return result


def get_pyodide_package_names(
    lockfile: Lockfile | None,
) -> list[str]:
    if lockfile is None:
        return []
    return [name for name, entry in lockfile.pyodide_packages.items() if entry.is_wasm]


def resolve_lockfile(
    dependencies: list[str],
    pyscript_version: str,
    lockfile_path: pathlib.Path,
) -> tuple[Lockfile | None, list[str]]:
    existing = load_lockfile(lockfile_path)
    if existing is not None:
        issues = validate_lockfile(existing, dependencies)
        if not issues:
            return existing, []
    lockfile, errors = generate_lockfile(dependencies, pyscript_version)
    save_lockfile(lockfile, lockfile_path)
    return lockfile, errors
