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
    source: Literal["explicit", "transitive"]
    is_pure_python: bool
    is_wasm: bool
    in_pyodide_cdn: bool
    pyodide_file_name: str | None = None
    pyodide_sha256: str | None = None
    pkg_dir: pathlib.Path | None = None


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


def _is_wasm_in_pyodide_lock(pkg_name: str, pyodide_lock: dict) -> bool:
    packages = pyodide_lock.get("packages", {})
    pkg_info = packages.get(pkg_name)
    if pkg_info is None:
        return False
    package_type = pkg_info.get("package_type")
    if package_type is not None:
        return package_type in ("shared_library", "cpython_module")
    file_name = pkg_info.get("file_name", "")
    return "pyodide" in file_name or "wasm32" in file_name


def _get_pyodide_sha256(pkg_name: str, pyodide_lock: dict) -> str | None:
    packages = pyodide_lock.get("packages", {})
    pkg_info = packages.get(pkg_name)
    if pkg_info is None:
        return None
    return pkg_info.get("sha256")


def _resolve_transitive_deps_local(package_name: str) -> set[str]:
    try:
        reqs = importlib.metadata.requires(package_name)
    except importlib.metadata.PackageNotFoundError:
        try:
            reqs = importlib.metadata.requires(package_name.replace("-", "_"))
        except importlib.metadata.PackageNotFoundError:
            return set()
    if reqs is None:
        return set()
    result: set[str] = set()
    for req_str in reqs:
        dep_part = req_str.split(";")[0].strip()
        marker_part = req_str.split(";")[1].strip() if ";" in req_str else ""
        if marker_part:
            try:
                from packaging.markers import Marker

                if not Marker(marker_part).evaluate():
                    continue
            except Exception:
                continue
        dep_name = dep_part.split(">")[0].split("<")[0].split("=")[0].split("!")[0].split("~")[0].strip()
        dep_name = dep_name.split("[")[0].strip()
        if dep_name and dep_name[0].isalpha():
            result.add(dep_name)
    return result


def classify_dependencies(
    dependencies: list[str],
    pyodide_lock: dict,
) -> tuple[list[ClassifiedDependency], list[str], list[str]]:
    classified: list[ClassifiedDependency] = []
    errors: list[str] = []
    warnings: list[str] = []
    seen: dict[str, ClassifiedDependency] = {}

    for dep_name in dependencies:
        norm_name = dep_name.replace("-", "_")
        if norm_name in seen:
            continue
        pkg_info = pyodide_lock.get("packages", {}).get(dep_name)
        if pkg_info is not None:
            is_wasm = _is_wasm_in_pyodide_lock(dep_name, pyodide_lock)
            version = pkg_info.get("version", "0.0.0")
            file_name = pkg_info.get("file_name", "")
            sha256 = _get_pyodide_sha256(dep_name, pyodide_lock)
            if is_wasm:
                classified_dep = ClassifiedDependency(
                    name=dep_name,
                    version=version,
                    source="explicit",
                    is_pure_python=False,
                    is_wasm=True,
                    in_pyodide_cdn=True,
                    pyodide_file_name=file_name,
                    pyodide_sha256=sha256,
                    pkg_dir=None,
                )
            else:
                pkg_dir = _find_package_dir(dep_name)
                classified_dep = ClassifiedDependency(
                    name=dep_name,
                    version=version,
                    source="explicit",
                    is_pure_python=True,
                    is_wasm=False,
                    in_pyodide_cdn=True,
                    pyodide_file_name=file_name,
                    pyodide_sha256=sha256,
                    pkg_dir=pkg_dir,
                )
            classified.append(classified_dep)
            seen[norm_name] = classified_dep
        else:
            pkg_dir = _find_package_dir(dep_name)
            if pkg_dir is None:
                errors.append(
                    f"Package '{dep_name}' not found locally and not in Pyodide CDN. "
                    f"Install it locally or add it to AppConfig.dependencies."
                )
                continue
            if not _is_pure_python_package(pkg_dir):
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
                in_pyodide_cdn=False,
                pyodide_file_name=None,
                pyodide_sha256=None,
                pkg_dir=pkg_dir,
            )
            classified.append(classified_dep)
            seen[norm_name] = classified_dep

    _resolve_all_transitives(classified, seen, pyodide_lock, errors, warnings)

    return classified, errors, warnings


def _resolve_all_transitives(
    classified: list[ClassifiedDependency],
    seen: dict[str, ClassifiedDependency],
    pyodide_lock: dict,
    errors: list[str],
    warnings: list[str],
) -> None:
    all_deps_to_process = list(classified)
    visited_for_transitive: set[str] = {d.name.replace("-", "_") for d in classified}

    while all_deps_to_process:
        dep = all_deps_to_process.pop(0)
        dep_name = dep.name

        transitive_names = list(_resolve_transitive_deps_via_pyodide_lock(dep_name, pyodide_lock))

        if not dep.in_pyodide_cdn and dep.pkg_dir is not None:
            local_transitives = _resolve_transitive_deps_local(dep_name)
            for lt in local_transitives:
                if lt not in transitive_names:
                    transitive_names.append(lt)

        for trans_name in transitive_names:
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
                file_name = pkg_info.get("file_name", "")
                sha256 = _get_pyodide_sha256(trans_name, pyodide_lock)
                if is_wasm:
                    classified_dep = ClassifiedDependency(
                        name=trans_name,
                        version=version,
                        source="transitive",
                        is_pure_python=False,
                        is_wasm=True,
                        in_pyodide_cdn=True,
                        pyodide_file_name=file_name,
                        pyodide_sha256=sha256,
                        pkg_dir=None,
                    )
                else:
                    pkg_dir = _find_package_dir(trans_name)
                    classified_dep = ClassifiedDependency(
                        name=trans_name,
                        version=version,
                        source="transitive",
                        is_pure_python=True,
                        is_wasm=False,
                        in_pyodide_cdn=True,
                        pyodide_file_name=file_name,
                        pyodide_sha256=sha256,
                        pkg_dir=pkg_dir,
                    )
                classified.append(classified_dep)
                seen[trans_norm] = classified_dep
                all_deps_to_process.append(classified_dep)
            else:
                pkg_dir = _find_package_dir(trans_name)
                if pkg_dir is None:
                    warnings.append(
                        f"Transitive dependency '{trans_name}' not found locally "
                        f"and not in Pyodide CDN. Consider adding it to AppConfig.dependencies."
                    )
                    continue
                if not _is_pure_python_package(pkg_dir):
                    continue
                version = _get_package_version(trans_name) or "0.0.0"
                classified_dep = ClassifiedDependency(
                    name=trans_name,
                    version=version,
                    source="transitive",
                    is_pure_python=True,
                    is_wasm=False,
                    in_pyodide_cdn=False,
                    pyodide_file_name=None,
                    pyodide_sha256=None,
                    pkg_dir=pkg_dir,
                )
                classified.append(classified_dep)
                seen[trans_norm] = classified_dep
                all_deps_to_process.append(classified_dep)
