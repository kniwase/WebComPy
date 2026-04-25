from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field

from webcompy.cli._pyodide_lock import PyodideLockFetchError, fetch_pyodide_lock, get_pyodide_version

LOCKFILE_VERSION = 1
LOCKFILE_NAME = "webcompy-lock.json"


@dataclass
class PyodidePackageEntry:
    version: str
    file_name: str
    is_wasm: bool
    source: str = "explicit"

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "file_name": self.file_name,
            "is_wasm": self.is_wasm,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PyodidePackageEntry:
        return cls(
            version=data["version"],
            file_name=data["file_name"],
            is_wasm=data["is_wasm"],
            source=data.get("source", "explicit"),
        )


@dataclass
class BundledPackageEntry:
    version: str
    source: str
    is_pure_python: bool
    from_pyodide_cdn: bool = False

    def to_dict(self) -> dict:
        d: dict = {
            "version": self.version,
            "source": self.source,
            "is_pure_python": self.is_pure_python,
        }
        if self.from_pyodide_cdn:
            d["from_pyodide_cdn"] = True
        return d

    @classmethod
    def from_dict(cls, data: dict) -> BundledPackageEntry:
        return cls(
            version=data["version"],
            source=data["source"],
            is_pure_python=data["is_pure_python"],
            from_pyodide_cdn=data.get("from_pyodide_cdn", False),
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
            "standalone_assets": {},
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
) -> tuple[Lockfile, list[str], list[str]]:
    if pyodide_version is None:
        pyodide_version = get_pyodide_version(pyscript_version)

    pyodide_lock = fetch_pyodide_lock(pyodide_version)

    from webcompy.cli._dependency_resolver import classify_dependencies

    classified, errors, warnings = classify_dependencies(dependencies, pyodide_lock)

    pyodide_packages: dict[str, PyodidePackageEntry] = {}
    bundled_packages: dict[str, BundledPackageEntry] = {}

    for dep in classified:
        if dep.is_cdn_package and not dep.is_bundled:
            pkg_info = pyodide_lock.get("packages", {}).get(dep.name, {})
            file_name = pkg_info.get("file_name", "")
            pyodide_packages[dep.name] = PyodidePackageEntry(
                version=dep.version,
                file_name=file_name,
                is_wasm=dep.is_wasm,
                source="transitive"
                if dep.source in ("transitive", "pyodide_cdn") and dep.name not in dependencies
                else "explicit",
            )
        else:
            if dep.source == "pyodide_cdn":
                lock_source = "explicit"
            elif dep.source in ("explicit", "transitive"):
                lock_source = dep.source
            else:
                lock_source = "transitive"
            bundled_packages[dep.name] = BundledPackageEntry(
                version=dep.version,
                source=lock_source,
                is_pure_python=dep.is_pure_python,
                from_pyodide_cdn=dep.source == "pyodide_cdn",
            )

    lockfile = Lockfile(
        pyodide_version=pyodide_version,
        pyscript_version=pyscript_version,
        pyodide_packages=pyodide_packages,
        bundled_packages=bundled_packages,
    )

    return lockfile, errors, warnings


def validate_lockfile(
    lockfile: Lockfile,
    dependencies: list[str],
) -> list[str]:
    issues: list[str] = []
    explicit_in_lock = {name for name, entry in lockfile.bundled_packages.items() if entry.source == "explicit"}
    explicit_pyodide = {name for name, entry in lockfile.pyodide_packages.items() if entry.source == "explicit"}
    all_explicit_in_lock = explicit_in_lock | explicit_pyodide
    dep_set = {d.replace("-", "_") for d in dependencies}
    lock_set = {n.replace("-", "_") for n in all_explicit_in_lock}
    missing = dep_set - lock_set
    if missing:
        issues.append(f"Dependencies missing from lock file: {', '.join(sorted(missing))}")
    return issues


def validate_local_environment(
    lockfile: Lockfile,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    from webcompy.cli._dependency_resolver import _find_package_dir, _get_package_version

    for name, entry in lockfile.bundled_packages.items():
        if not entry.is_pure_python:
            continue
        pkg_dir = _find_package_dir(name)
        if pkg_dir is None:
            if entry.from_pyodide_cdn:
                warnings.append(
                    f"Package '{name}' (version {entry.version} from Pyodide CDN) "
                    f"is not installed locally. SSR/SSG may fail if this package is imported server-side."
                )
            else:
                errors.append(
                    f"Package '{name}' (version {entry.version}) listed in lock file "
                    f"is not installed locally. Install it with: pip install {name}=={entry.version}"
                )
            continue
        local_version = _get_package_version(name)
        if local_version is not None and local_version != entry.version:
            if entry.from_pyodide_cdn:
                warnings.append(
                    f"Package '{name}' version mismatch: lock file has {entry.version} (Pyodide CDN), "
                    f"local has {local_version}. "
                    f"The local version will be used for SSR/SSG, "
                    f"while the Pyodide CDN version will be used in the browser."
                )
            else:
                errors.append(
                    f"Package '{name}' version mismatch: lock file has {entry.version}, "
                    f"local has {local_version}. "
                    f"Install the correct version with: pip install {name}=={entry.version}"
                )

    for name, entry in lockfile.pyodide_packages.items():
        if entry.is_wasm:
            continue
        local_version = _get_package_version(name)
        if local_version is not None and local_version != entry.version:
            warnings.append(
                f"Package '{name}' version mismatch: lock file has {entry.version}, "
                f"local has {local_version}. "
                f"The local version will be used for SSR/SSG, "
                f"while the Pyodide CDN version will be used in the browser."
            )

    return errors, warnings


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
    return result


def get_pyodide_package_names(
    lockfile: Lockfile | None,
) -> list[str]:
    if lockfile is None:
        return []
    result: list[str] = []
    for name, entry in lockfile.pyodide_packages.items():
        if entry.is_wasm:
            result.append(name)
    return result


def resolve_lockfile(
    dependencies: list[str],
    pyscript_version: str,
    lockfile_path: pathlib.Path,
) -> tuple[Lockfile | None, list[str], list[str]]:
    existing = load_lockfile(lockfile_path)
    if existing is not None:
        issues = validate_lockfile(existing, dependencies)
        if not issues:
            return existing, [], []
    try:
        lockfile, errors, warnings = generate_lockfile(dependencies, pyscript_version)
    except PyodideLockFetchError as e:
        if existing is not None:
            return existing, [str(e)], []
        return None, [str(e)], []
    save_lockfile(lockfile, lockfile_path)
    return lockfile, errors, warnings
