from __future__ import annotations

import importlib.metadata
import importlib.util
import pathlib
from dataclasses import dataclass
from typing import Literal


@dataclass
class ClassifiedDependency:
    name: str
    version: str
    source: Literal["pyodide_cdn", "explicit", "transitive"]
    is_pure_python: bool
    is_wasm: bool
    pkg_dir: pathlib.Path | None

    @property
    def is_bundled(self) -> bool:
        return self.is_pure_python


def _is_pure_python_package(pkg_dir: pathlib.Path) -> bool:
    for _root, _dirs, files in pkg_dir.walk():
        for f in files:
            if f.endswith((".so", ".pyd", ".dylib")):
                return False
    return True


def _find_package_dir(package_name: str) -> pathlib.Path | None:
    normalized = package_name.replace("-", "_").replace(".", "_")
    spec = importlib.util.find_spec(normalized)
    if spec is None:
        spec = importlib.util.find_spec(package_name)
    if spec is None:
        return None
    if spec.origin is None:
        if spec.submodule_search_locations:
            for loc in spec.submodule_search_locations:
                p = pathlib.Path(loc)
                if p.is_dir():
                    return p
        return None
    origin = pathlib.Path(spec.origin)
    if origin.is_file() and origin.name == "__init__.py":
        return origin.parent
    if origin.is_file():
        return origin.parent
    return None


def _get_package_version(package_name: str) -> str | None:
    normalized = package_name.replace("-", "_")
    try:
        return importlib.metadata.version(normalized)
    except importlib.metadata.PackageNotFoundError:
        pass
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _resolve_transitive_deps_via_pyodide_lock(
    package_name: str,
    pyodide_lock: dict,
    visited: set[str] | None = None,
) -> set[str]:
    if visited is None:
        visited = set()
    if package_name in visited:
        return set()
    visited.add(package_name)
    packages = pyodide_lock.get("packages", {})
    pkg_info = packages.get(package_name)
    if pkg_info is None:
        return set()
    result: set[str] = set()
    for dep in pkg_info.get("depends", []):
        dep_name = dep.split("[")[0].split(";")[0].strip()
        if dep_name and dep_name in packages:
            result.add(dep_name)
            result |= _resolve_transitive_deps_via_pyodide_lock(dep_name, pyodide_lock, visited)
    return result


def _resolve_transitive_deps_local(package_name: str) -> list[str]:
    result: list[str] = []
    visited: set[str] = set()
    _walk_requires_dist(package_name, result, visited)
    return result


def _walk_requires_dist(package_name: str, result: list[str], visited: set[str]) -> None:
    normalized = package_name.replace("-", "_")
    if normalized in visited:
        return
    visited.add(normalized)
    try:
        dist = importlib.metadata.distribution(normalized)
    except importlib.metadata.PackageNotFoundError:
        try:
            dist = importlib.metadata.distribution(package_name)
        except importlib.metadata.PackageNotFoundError:
            return
    requires = dist.requires
    if requires is None:
        return
    for req_str in requires:
        req_name = (
            req_str.split("[")[0]
            .split(";")[0]
            .split(">")[0]
            .split("<")[0]
            .split("=")[0]
            .split("!")[0]
            .split("~")[0]
            .strip()
        )
        if not req_name:
            continue
        req_normalized = req_name.replace("-", "_")
        if req_normalized not in visited:
            result.append(req_name)
            _walk_requires_dist(req_name, result, visited)


def _is_wasm_in_pyodide_lock(pkg_name: str, pyodide_lock: dict) -> bool:
    packages = pyodide_lock.get("packages", {})
    pkg_info = packages.get(pkg_name)
    if pkg_info is None:
        return False
    file_name = pkg_info.get("file_name", "")
    return "pyodide" in file_name or "wasm32" in file_name


def classify_dependencies(
    dependencies: list[str],
    pyodide_lock: dict | None,
) -> tuple[list[ClassifiedDependency], list[str]]:
    classified: list[ClassifiedDependency] = []
    errors: list[str] = []
    seen: dict[str, ClassifiedDependency] = {}

    lock_unavailable = pyodide_lock is None
    if pyodide_lock is None:
        pyodide_lock = {}

    for dep_name in dependencies:
        norm_name = dep_name.replace("-", "_")
        if norm_name in seen:
            continue
        pkg_info = pyodide_lock.get("packages", {}).get(dep_name)
        if pkg_info is not None:
            is_wasm = _is_wasm_in_pyodide_lock(dep_name, pyodide_lock)
            version = pkg_info.get("version", "0.0.0")
            if is_wasm:
                classified_dep = ClassifiedDependency(
                    name=dep_name,
                    version=version,
                    source="pyodide_cdn",
                    is_pure_python=False,
                    is_wasm=True,
                    pkg_dir=None,
                )
                classified.append(classified_dep)
                seen[norm_name] = classified_dep
            else:
                pkg_dir = _find_package_dir(dep_name)
                classified_dep = ClassifiedDependency(
                    name=dep_name,
                    version=version,
                    source="pyodide_cdn",
                    is_pure_python=True,
                    is_wasm=False,
                    pkg_dir=pkg_dir,
                )
                classified.append(classified_dep)
                seen[norm_name] = classified_dep
        else:
            pkg_dir = _find_package_dir(dep_name)
            if pkg_dir is None:
                if lock_unavailable:
                    errors.append(
                        f"Package '{dep_name}' not found locally and Pyodide lock is unavailable. "
                        f"Install it locally or add it to AppConfig.dependencies."
                    )
                else:
                    errors.append(
                        f"Package '{dep_name}' not found locally and not in Pyodide CDN. "
                        f"Install it locally or add it to AppConfig.dependencies."
                    )
                continue
            if not _is_pure_python_package(pkg_dir):
                if lock_unavailable:
                    errors.append(
                        f"Package '{dep_name}' is a C extension not available in Pyodide. "
                        f"Consider using a pure-Python alternative."
                    )
                else:
                    errors.append(
                        f"Package '{dep_name}' is a C extension and is not available in Pyodide. "
                        f"Consider using a pure-Python alternative."
                    )
                continue
            version = _get_package_version(dep_name) or "0.0.0"
            classified_dep = ClassifiedDependency(
                name=dep_name,
                version=version,
                source="explicit",
                is_pure_python=True,
                is_wasm=False,
                pkg_dir=pkg_dir,
            )
            classified.append(classified_dep)
            seen[norm_name] = classified_dep

    _resolve_all_transitives(classified, seen, pyodide_lock, errors, lock_unavailable)

    return classified, errors


def _resolve_all_transitives(
    classified: list[ClassifiedDependency],
    seen: dict[str, ClassifiedDependency],
    pyodide_lock: dict,
    errors: list[str],
    lock_unavailable: bool,
) -> None:
    all_deps_to_process = list(classified)
    visited_for_transitive: set[str] = {d.name.replace("-", "_") for d in classified}

    while all_deps_to_process:
        dep = all_deps_to_process.pop(0)
        dep_name = dep.name

        pyodide_transitives = _resolve_transitive_deps_via_pyodide_lock(dep_name, pyodide_lock)
        local_transitives: list[str] = []
        if dep.pkg_dir is not None or dep.source in ("explicit", "transitive"):
            local_transitives = _resolve_transitive_deps_local(dep_name)

        all_transitive_names: list[str] = []
        seen_transitive: set[str] = set()
        for t in pyodide_transitives:
            if t not in seen_transitive:
                seen_transitive.add(t)
                all_transitive_names.append(t)
        for t in local_transitives:
            t_norm = t.replace("-", "_")
            if t_norm not in seen_transitive:
                seen_transitive.add(t_norm)
                all_transitive_names.append(t)

        for trans_name in all_transitive_names:
            trans_norm = trans_name.replace("-", "_")
            if trans_norm in seen:
                continue
            if trans_norm in visited_for_transitive:
                continue
            visited_for_transitive.add(trans_norm)

            pkg_info = pyodide_lock.get("packages", {}).get(trans_name)
            if pkg_info is not None:
                is_wasm = _is_wasm_in_pyodide_lock(trans_name, pyodide_lock)
                version = pkg_info.get("version", "0.0.0")
                if is_wasm:
                    classified_dep = ClassifiedDependency(
                        name=trans_name,
                        version=version,
                        source="transitive",
                        is_pure_python=False,
                        is_wasm=True,
                        pkg_dir=None,
                    )
                    classified.append(classified_dep)
                    seen[trans_norm] = classified_dep
                    all_deps_to_process.append(classified_dep)
                else:
                    pkg_dir = _find_package_dir(trans_name)
                    classified_dep = ClassifiedDependency(
                        name=trans_name,
                        version=version,
                        source="transitive",
                        is_pure_python=True,
                        is_wasm=False,
                        pkg_dir=pkg_dir,
                    )
                    classified.append(classified_dep)
                    seen[trans_norm] = classified_dep
                    all_deps_to_process.append(classified_dep)
            else:
                pkg_dir = _find_package_dir(trans_name)
                if pkg_dir is None:
                    if lock_unavailable:
                        errors.append(
                            f"Transitive dependency '{trans_name}' not found locally and Pyodide lock is unavailable. "
                            f"Install it locally or add it to AppConfig.dependencies."
                        )
                    else:
                        errors.append(
                            f"Transitive dependency '{trans_name}' not found locally and not in Pyodide CDN. "
                            f"Install it locally or add it to AppConfig.dependencies."
                        )
                    continue
                if not _is_pure_python_package(pkg_dir):
                    if lock_unavailable:
                        errors.append(
                            f"Transitive dependency '{trans_name}' is a C extension not available in Pyodide."
                        )
                    else:
                        errors.append(
                            f"Transitive dependency '{trans_name}' is a C extension and is not available in Pyodide."
                        )
                    continue
                version = _get_package_version(trans_name) or "0.0.0"
                classified_dep = ClassifiedDependency(
                    name=trans_name,
                    version=version,
                    source="transitive",
                    is_pure_python=True,
                    is_wasm=False,
                    pkg_dir=pkg_dir,
                )
                classified.append(classified_dep)
                seen[trans_norm] = classified_dep
                all_deps_to_process.append(classified_dep)
