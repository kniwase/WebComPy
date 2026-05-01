from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field

from webcompy.cli._pyodide_lock import PyodideLockFetchError, fetch_pyodide_lock, get_pyodide_version

LOCKFILE_VERSION = 2
LOCKFILE_NAME = "webcompy-lock.json"


@dataclass
class WasmPackageEntry:
    version: str
    file_name: str
    sha256: str | None = None
    source: str = "explicit"

    def to_dict(self) -> dict:
        d: dict = {
            "version": self.version,
            "file_name": self.file_name,
            "source": self.source,
        }
        if self.sha256 is not None:
            d["sha256"] = self.sha256
        return d

    @classmethod
    def from_dict(cls, data: dict) -> WasmPackageEntry:
        return cls(
            version=data["version"],
            file_name=data["file_name"],
            sha256=data.get("sha256"),
            source=data.get("source", "explicit"),
        )


@dataclass
class PurePythonPackageEntry:
    version: str
    source: str
    in_pyodide_cdn: bool
    pyodide_file_name: str | None = None
    pyodide_sha256: str | None = None

    def to_dict(self) -> dict:
        d: dict = {
            "version": self.version,
            "source": self.source,
            "in_pyodide_cdn": self.in_pyodide_cdn,
        }
        if self.in_pyodide_cdn and self.pyodide_file_name is not None:
            d["pyodide_file_name"] = self.pyodide_file_name
        if self.in_pyodide_cdn and self.pyodide_sha256 is not None:
            d["pyodide_sha256"] = self.pyodide_sha256
        return d

    @classmethod
    def from_dict(cls, data: dict) -> PurePythonPackageEntry:
        return cls(
            version=data["version"],
            source=data["source"],
            in_pyodide_cdn=data["in_pyodide_cdn"],
            pyodide_file_name=data.get("pyodide_file_name"),
            pyodide_sha256=data.get("pyodide_sha256"),
        )


@dataclass
class RuntimeAssetEntry:
    url: str
    sha256: str | None = None

    def to_dict(self) -> dict:
        d: dict = {"url": self.url}
        if self.sha256 is not None:
            d["sha256"] = self.sha256
        return d

    @classmethod
    def from_dict(cls, data: dict) -> RuntimeAssetEntry:
        return cls(
            url=data["url"],
            sha256=data.get("sha256"),
        )


@dataclass
class Lockfile:
    pyodide_version: str
    pyscript_version: str
    wasm_packages: dict[str, WasmPackageEntry] = field(default_factory=dict)
    pure_python_packages: dict[str, PurePythonPackageEntry] = field(default_factory=dict)
    wasm_serving: str = "cdn"
    runtime_serving: str = "cdn"
    runtime_assets: dict[str, RuntimeAssetEntry] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict = {
            "version": LOCKFILE_VERSION,
            "pyodide_version": self.pyodide_version,
            "pyscript_version": self.pyscript_version,
            "wasm_serving": self.wasm_serving,
            "runtime_serving": self.runtime_serving,
            "wasm_packages": {name: entry.to_dict() for name, entry in self.wasm_packages.items()},
            "pure_python_packages": {name: entry.to_dict() for name, entry in self.pure_python_packages.items()},
        }
        if self.runtime_serving == "local" and self.runtime_assets:
            d["runtime_assets"] = {name: entry.to_dict() for name, entry in self.runtime_assets.items()}
        return d


def load_lockfile(path: pathlib.Path) -> Lockfile | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("version") != LOCKFILE_VERSION:
        return None
    wasm_packages = {name: WasmPackageEntry.from_dict(entry) for name, entry in data.get("wasm_packages", {}).items()}
    pure_python_packages = {
        name: PurePythonPackageEntry.from_dict(entry) for name, entry in data.get("pure_python_packages", {}).items()
    }
    runtime_assets_data = data.get("runtime_assets") or data.get("standalone_assets")
    runtime_assets: dict[str, RuntimeAssetEntry] = {}
    if runtime_assets_data:
        runtime_assets = {name: RuntimeAssetEntry.from_dict(entry) for name, entry in runtime_assets_data.items()}
    return Lockfile(
        pyodide_version=data["pyodide_version"],
        pyscript_version=data["pyscript_version"],
        wasm_packages=wasm_packages,
        pure_python_packages=pure_python_packages,
        wasm_serving=data.get("wasm_serving", "cdn"),
        runtime_serving=data.get("runtime_serving", "cdn"),
        runtime_assets=runtime_assets,
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
    wasm_serving: str = "cdn",
    runtime_serving: str = "cdn",
) -> tuple[Lockfile, list[str], list[str]]:
    if pyodide_version is None:
        pyodide_version = get_pyodide_version(pyscript_version)

    pyodide_lock = fetch_pyodide_lock(pyodide_version)

    from webcompy.cli._dependency_resolver import PackageKind, classify_dependencies

    classified, errors, warnings = classify_dependencies(dependencies, pyodide_lock)

    wasm_packages: dict[str, WasmPackageEntry] = {}
    pure_python_packages: dict[str, PurePythonPackageEntry] = {}

    for dep in classified:
        lock_source = dep.source
        if dep.kind == PackageKind.WASM:
            pkg_info = pyodide_lock.get("packages", {}).get(dep.name, {})
            file_name = pkg_info.get("file_name", "")
            sha256 = dep.pyodide_sha256
            wasm_packages[dep.name] = WasmPackageEntry(
                version=dep.version,
                file_name=file_name,
                sha256=sha256,
                source=lock_source,
            )
        elif dep.kind in (PackageKind.CDN_PURE_PYTHON, PackageKind.LOCAL_PURE_PYTHON):
            is_cdn = dep.kind == PackageKind.CDN_PURE_PYTHON
            entry = PurePythonPackageEntry(
                version=dep.version,
                source=lock_source,
                in_pyodide_cdn=is_cdn,
                pyodide_file_name=dep.pyodide_file_name if is_cdn else None,
                pyodide_sha256=dep.pyodide_sha256 if is_cdn else None,
            )
            pure_python_packages[dep.name] = entry

    lockfile = Lockfile(
        pyodide_version=pyodide_version,
        pyscript_version=pyscript_version,
        wasm_packages=wasm_packages,
        pure_python_packages=pure_python_packages,
        wasm_serving=wasm_serving,
        runtime_serving=runtime_serving,
    )

    return lockfile, errors, warnings


def validate_lockfile(
    lockfile: Lockfile,
    dependencies: list[str],
) -> list[str]:
    issues: list[str] = []
    explicit_pp = {name for name, entry in lockfile.pure_python_packages.items() if entry.source == "explicit"}
    explicit_wasm = {name for name, entry in lockfile.wasm_packages.items() if entry.source == "explicit"}
    all_explicit_in_lock = explicit_pp | explicit_wasm
    dep_set = {d.replace("-", "_") for d in dependencies}
    lock_set = {n.replace("-", "_") for n in all_explicit_in_lock}
    missing = dep_set - lock_set
    if missing:
        issues.append(f"Dependencies missing from lock file: {', '.join(sorted(missing))}")
    return issues


def validate_local_environment(
    lockfile: Lockfile,
    serve_all_deps: bool = True,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    from webcompy.cli._dependency_resolver import _find_package_dir, _get_package_version

    for name, entry in lockfile.pure_python_packages.items():
        if entry.in_pyodide_cdn:
            local_version = _get_package_version(name)
            if local_version is not None and local_version != entry.version:
                warnings.append(
                    f"Package '{name}' version mismatch: lock file has {entry.version}, "
                    f"local has {local_version}. "
                    f"The local version will be used for SSR/SSG, "
                    f"while the CDN version will be used in the browser."
                )
            elif local_version is None:
                warnings.append(
                    f"Package '{name}' (version {entry.version}) is available in the Pyodide CDN "
                    f"and will be {'downloaded and bundled' if serve_all_deps else 'loaded from CDN'}. "
                    f"It is not installed locally, which may affect SSR/SSG."
                )
        else:
            pkg_dir = _find_package_dir(name)
            if pkg_dir is None:
                errors.append(
                    f"Package '{name}' (version {entry.version}) listed in lock file "
                    f"is not installed locally. Install it with: pip install {name}=={entry.version}"
                )
                continue
            local_version = _get_package_version(name)
            if local_version is None or local_version != entry.version:
                if local_version is None:
                    errors.append(
                        f"Package '{name}' version could not be determined locally, "
                        f"but lock file requires {entry.version}. "
                        f"Ensure the package is properly installed with: pip install {name}=={entry.version}"
                    )
                else:
                    errors.append(
                        f"Package '{name}' version mismatch: lock file has {entry.version}, "
                        f"local has {local_version}. "
                        f"Install the correct version with: pip install {name}=={entry.version}"
                    )

    return errors, warnings


def get_bundled_deps(
    lockfile: Lockfile | None,
    serve_all_deps: bool = True,
) -> list[tuple[str, pathlib.Path]]:
    if lockfile is None:
        return []
    from webcompy.cli._dependency_resolver import _find_package_dir

    result: list[tuple[str, pathlib.Path]] = []
    seen: set[str] = set()
    for name, entry in lockfile.pure_python_packages.items():
        if entry.in_pyodide_cdn:
            continue
        norm = name.replace("-", "_")
        if norm in seen:
            continue
        seen.add(norm)
        pkg_dir = _find_package_dir(name)
        if pkg_dir is not None:
            result.append((name, pkg_dir))
    return result


def get_wasm_package_names(
    lockfile: Lockfile | None,
) -> list[str]:
    if lockfile is None:
        return []
    return list(lockfile.wasm_packages.keys())


def get_cdn_pure_python_package_names(
    lockfile: Lockfile | None,
) -> list[str]:
    if lockfile is None:
        return []
    return [name for name, entry in lockfile.pure_python_packages.items() if entry.in_pyodide_cdn]


def resolve_lockfile(
    dependencies: list[str],
    pyscript_version: str,
    lockfile_path: pathlib.Path,
    wasm_serving: str = "cdn",
    runtime_serving: str = "cdn",
) -> tuple[Lockfile | None, list[str], list[str]]:
    existing = load_lockfile(lockfile_path)
    if existing is not None:
        issues = validate_lockfile(existing, dependencies)
        if not issues:
            return existing, [], []
    try:
        lockfile, errors, warnings = generate_lockfile(
            dependencies, pyscript_version, wasm_serving=wasm_serving, runtime_serving=runtime_serving
        )
    except PyodideLockFetchError as e:
        if existing is not None:
            return existing, [str(e)], []
        return None, [str(e)], []
    save_lockfile(lockfile, lockfile_path)
    return lockfile, errors, warnings
