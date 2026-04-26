from __future__ import annotations

import base64
import hashlib
import os
import pathlib
import re
import zipfile

_BROWSER_ONLY_EXCLUDE = {"cli"}


def _filter_excluded_subpackages(
    packages: list[str],
    top_level_name: str,
    exclude: set[str],
) -> list[str]:
    if not exclude:
        return packages
    return [pkg for pkg in packages if not (pkg.startswith(f"{top_level_name}.") and pkg.split(".")[1] in exclude)]


def _discover_packages(package_dir: pathlib.Path) -> list[str]:
    packages: list[str] = []
    if not package_dir.is_dir():
        return packages
    for root, dirs, files in os.walk(package_dir):
        if "__init__.py" in files:
            rel = pathlib.Path(root).relative_to(package_dir.parent)
            packages.append(str(rel).replace(os.sep, "."))
        dirs[:] = [d for d in dirs if d != "__pycache__"]
    return sorted(packages)


def _collect_package_files(
    package_dir: pathlib.Path,
    packages: list[str],
    package_data: dict[str, list[str]] | None = None,
) -> list[tuple[pathlib.Path, str]]:
    files: list[tuple[pathlib.Path, str]] = []
    parent = package_dir.parent
    seen: set[str] = set()
    for pkg in packages:
        pkg_rel = pkg.replace(".", os.sep)
        pkg_path = parent / pkg_rel
        if not pkg_path.is_dir():
            continue
        for root, _dirs, filenames in os.walk(pkg_path):
            root_path = pathlib.Path(root)
            for filename in filenames:
                filepath = root_path / filename
                arc_path = str(filepath.relative_to(parent)).replace(os.sep, "/")
                if arc_path in seen:
                    continue
                if filename.endswith((".py", ".pyi")) or filename == "py.typed":
                    seen.add(arc_path)
                    files.append((filepath, arc_path))
        if package_data and pkg in package_data:
            for pattern in package_data[pkg]:
                data_pkg_rel = pkg.replace(".", os.sep)
                for filepath in sorted(pathlib.Path(parent / data_pkg_rel).glob(pattern)):
                    if filepath.is_file():
                        arc_path = str(filepath.relative_to(parent)).replace(os.sep, "/")
                        if arc_path not in seen:
                            seen.add(arc_path)
                            files.append((filepath, arc_path))
    return files


def _sha256_b64(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name).lower()


def get_wheel_filename(name: str, version: str) -> str:
    return f"{_normalize_name(name)}-{version}-py3-none-any.whl"


def _content_hash_wheel(wheel_path: pathlib.Path, name: str) -> pathlib.Path:
    digest = hashlib.sha256(wheel_path.read_bytes()).hexdigest()[:8]
    new_filename = f"{_normalize_name(name)}-0+sha.{digest}-py3-none-any.whl"
    new_path = wheel_path.parent / new_filename
    wheel_path.rename(new_path)
    return new_path


def _write_metadata(name: str, version: str) -> str:
    return f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n"


def _write_wheel() -> str:
    return "Wheel-Version: 1.0\nGenerator: webcompy\nRoot-Is-Purelib: true\nTag: py3-none-any\n"


def _write_record(
    entries: list[tuple[str, str, int]],
    dist_info: str,
) -> str:
    lines: list[str] = []
    for arc_path, hash_val, size in entries:
        lines.append(f"{arc_path},{hash_val},{size}")
    record_path = f"{dist_info}/RECORD"
    lines.append(f"{record_path},,")
    return "\n".join(lines) + "\n"


def _assets_to_package_data(
    app_package_name: str,
    assets: dict[str, str],
    app_package_dir: pathlib.Path,
) -> dict[str, list[str]]:
    package_data: dict[str, list[str]] = {}
    patterns: set[str] = set()
    for _key, rel_path in assets.items():
        full_path = app_package_dir / rel_path
        if full_path.is_file():
            directory = str(pathlib.Path(rel_path).parent)
            pattern = pathlib.Path(rel_path).name
            glob_pattern = str(pathlib.Path(directory) / pattern).replace(os.sep, "/") if directory != "." else pattern
        else:
            glob_pattern = rel_path.replace(os.sep, "/")
        if glob_pattern not in patterns:
            patterns.add(glob_pattern)
    package_data[app_package_name] = list(patterns)
    return package_data


def _generate_assets_registry(
    app_package_name: str,
    assets: dict[str, str],
) -> str:
    entries = ", ".join(f'"{key}": "{app_package_name}/{rel_path}"' for key, rel_path in assets.items())
    return f"_REGISTRY: dict[str, str] = {{{entries}}}\n"


def make_wheel(
    name: str,
    package_dir: pathlib.Path,
    dest: pathlib.Path,
    version: str,
    package_data: dict[str, list[str]] | None = None,
) -> pathlib.Path:
    packages = _discover_packages(package_dir)
    files = _collect_package_files(package_dir, packages, package_data)
    dist_name = _normalize_name(name)
    dist_info = f"{dist_name}-{version}.dist-info"
    top_levels: set[str] = set()
    for pkg in packages:
        top_levels.add(pkg.split(".")[0])
    wheel_filename = get_wheel_filename(name, version)
    wheel_path = dest / wheel_filename
    if wheel_path.exists():
        os.remove(wheel_path)

    record_entries: list[tuple[str, str, int]] = []
    metadata_content = _write_metadata(name, version)
    metadata_path = f"{dist_info}/METADATA"
    wheel_content = _write_wheel()
    wheel_meta_path = f"{dist_info}/WHEEL"
    top_level_content = "\n".join(sorted(top_levels)) + "\n"
    top_level_path = f"{dist_info}/top_level.txt"

    with zipfile.ZipFile(wheel_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for filepath, arc_path in files:
            data = filepath.read_bytes()
            zf.writestr(arc_path, data)
            record_entries.append((arc_path, _sha256_b64(data), len(data)))

        zf.writestr(metadata_path, metadata_content)
        record_entries.append(
            (metadata_path, _sha256_b64(metadata_content.encode("utf-8")), len(metadata_content.encode("utf-8")))
        )
        zf.writestr(wheel_meta_path, wheel_content)
        record_entries.append(
            (wheel_meta_path, _sha256_b64(wheel_content.encode("utf-8")), len(wheel_content.encode("utf-8")))
        )
        zf.writestr(top_level_path, top_level_content)
        record_entries.append(
            (top_level_path, _sha256_b64(top_level_content.encode("utf-8")), len(top_level_content.encode("utf-8")))
        )

        record_content = _write_record(record_entries, dist_info)
        zf.writestr(f"{dist_info}/RECORD", record_content)

    return wheel_path


def make_bundled_wheel(
    name: str,
    package_dirs: list[tuple[str, pathlib.Path]],
    dest: pathlib.Path,
    version: str,
    package_data: dict[str, list[str]] | None = None,
    extra_files: list[tuple[str, bytes]] | None = None,
) -> pathlib.Path:
    dist_name = _normalize_name(name)
    dist_info = f"{dist_name}-{version}.dist-info"
    top_levels: set[str] = set()
    record_entries: list[tuple[str, str, int]] = []
    wheel_filename = get_wheel_filename(name, version)
    wheel_path = dest / wheel_filename
    if wheel_path.exists():
        os.remove(wheel_path)

    all_files: list[tuple[pathlib.Path, str]] = []
    seen: set[str] = set()
    for _, pkg_dir in package_dirs:
        packages = _discover_packages(pkg_dir)
        files = _collect_package_files(pkg_dir, packages, package_data)
        for filepath, arc_path in files:
            if arc_path not in seen:
                seen.add(arc_path)
                all_files.append((filepath, arc_path))
        for pkg in packages:
            top_levels.add(pkg.split(".")[0])

    metadata_content = _write_metadata(name, version)
    metadata_path = f"{dist_info}/METADATA"
    wheel_content = _write_wheel()
    wheel_meta_path = f"{dist_info}/WHEEL"
    top_level_content = "\n".join(sorted(top_levels)) + "\n"
    top_level_path = f"{dist_info}/top_level.txt"

    with zipfile.ZipFile(wheel_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for filepath, arc_path in all_files:
            data = filepath.read_bytes()
            zf.writestr(arc_path, data)
            record_entries.append((arc_path, _sha256_b64(data), len(data)))

        if extra_files:
            for arc_path, content in extra_files:
                zf.writestr(arc_path, content)
                record_entries.append((arc_path, _sha256_b64(content), len(content)))

        zf.writestr(metadata_path, metadata_content)
        record_entries.append(
            (metadata_path, _sha256_b64(metadata_content.encode("utf-8")), len(metadata_content.encode("utf-8")))
        )
        zf.writestr(wheel_meta_path, wheel_content)
        record_entries.append(
            (wheel_meta_path, _sha256_b64(wheel_content.encode("utf-8")), len(wheel_content.encode("utf-8")))
        )
        zf.writestr(top_level_path, top_level_content)
        record_entries.append(
            (top_level_path, _sha256_b64(top_level_content.encode("utf-8")), len(top_level_content.encode("utf-8")))
        )

        record_content = _write_record(record_entries, dist_info)
        zf.writestr(f"{dist_info}/RECORD", record_content)

    return wheel_path


def make_webcompy_app_package(
    dest: pathlib.Path,
    webcompy_package_dir: pathlib.Path,
    package_dir: pathlib.Path,
    app_version: str,
    assets: dict[str, str] | None = None,
    bundled_deps: list[tuple[str, pathlib.Path]] | None = None,
) -> pathlib.Path:
    app_name = package_dir.name
    package_data: dict[str, list[str]] | None = None
    extra_files: list[tuple[str, bytes]] | None = None

    if assets:
        package_data = _assets_to_package_data(app_name, assets, package_dir)
        registry_content = _generate_assets_registry(app_name, assets)
        registry_arc_path = f"{app_name}/_assets_registry.py"
        extra_files = [(registry_arc_path, registry_content.encode("utf-8"))]

    package_dirs: list[tuple[str, pathlib.Path]] = [
        ("webcompy", webcompy_package_dir),
        (app_name, package_dir),
    ]
    if bundled_deps:
        package_dirs.extend(bundled_deps)

    dist_name = _normalize_name(app_name)
    dist_info = f"{dist_name}-{app_version}.dist-info"
    top_levels: set[str] = set()
    record_entries: list[tuple[str, str, int]] = []
    tmp_filename = f"{_normalize_name(app_name)}-0-py3-none-any.whl"
    wheel_path = dest / tmp_filename
    if wheel_path.exists():
        os.remove(wheel_path)

    all_files: list[tuple[pathlib.Path, str]] = []
    seen: set[str] = set()

    for pkg_name, pkg_dir in package_dirs:
        packages = _discover_packages(pkg_dir)
        if pkg_name == "webcompy":
            packages = _filter_excluded_subpackages(packages, "webcompy", _BROWSER_ONLY_EXCLUDE)
        files = _collect_package_files(pkg_dir, packages, package_data if pkg_name == app_name else None)
        for filepath, arc_path in files:
            if pkg_name == "webcompy":
                parts = pathlib.Path(arc_path).parts
                if len(parts) > 1 and parts[1] in _BROWSER_ONLY_EXCLUDE:
                    continue
            if arc_path not in seen:
                seen.add(arc_path)
                all_files.append((filepath, arc_path))
        for pkg in packages:
            top_levels.add(pkg.split(".")[0])

    metadata_content = _write_metadata(app_name, app_version)
    metadata_path = f"{dist_info}/METADATA"
    wheel_content = _write_wheel()
    wheel_meta_path = f"{dist_info}/WHEEL"
    top_level_content = "\n".join(sorted(top_levels)) + "\n"
    top_level_path = f"{dist_info}/top_level.txt"

    with zipfile.ZipFile(wheel_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for filepath, arc_path in all_files:
            data = filepath.read_bytes()
            zf.writestr(arc_path, data)
            record_entries.append((arc_path, _sha256_b64(data), len(data)))

        if extra_files:
            for arc_path, content in extra_files:
                zf.writestr(arc_path, content)
                record_entries.append((arc_path, _sha256_b64(content), len(content)))

        zf.writestr(metadata_path, metadata_content)
        record_entries.append(
            (metadata_path, _sha256_b64(metadata_content.encode("utf-8")), len(metadata_content.encode("utf-8")))
        )
        zf.writestr(wheel_meta_path, wheel_content)
        record_entries.append(
            (wheel_meta_path, _sha256_b64(wheel_content.encode("utf-8")), len(wheel_content.encode("utf-8")))
        )
        zf.writestr(top_level_path, top_level_content)
        record_entries.append(
            (top_level_path, _sha256_b64(top_level_content.encode("utf-8")), len(top_level_content.encode("utf-8")))
        )

        record_content = _write_record(record_entries, dist_info)
        zf.writestr(f"{dist_info}/RECORD", record_content)

    return _content_hash_wheel(wheel_path, app_name)
