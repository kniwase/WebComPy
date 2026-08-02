from __future__ import annotations

import base64
import hashlib
import os
import pathlib
import re
import zipfile

_DETERMINISTIC_DATE_TIME = (1980, 1, 1, 0, 0, 0)


def _write_zip_entry(zf: zipfile.ZipFile, arc_path: str, data: bytes | str) -> None:
    info = zipfile.ZipInfo(arc_path, date_time=_DETERMINISTIC_DATE_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, data)


def _discover_packages(package_dir: pathlib.Path) -> list[str]:
    packages: list[str] = []
    if not package_dir.is_dir():
        return packages
    for root, dirs, files in os.walk(package_dir):
        if "__init__.py" in files:
            rel = pathlib.Path(root).relative_to(package_dir.parent)
            packages.append(str(rel).replace(os.sep, "."))
        elif root == str(package_dir):
            for filename in files:
                if filename.endswith(".py") and filename != "__init__.py":
                    module_name = filename[:-3]
                    packages.append(module_name)
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
        single_module_py = pkg_path / f"{pkg}.py"
        if pkg_path.is_dir() and not (pkg_path / "__init__.py").exists():
            if single_module_py.is_file():
                arc_path = f"{pkg}.py"
                if arc_path not in seen:
                    seen.add(arc_path)
                    files.append((single_module_py, arc_path))
                continue
            continue
        if not pkg_path.is_dir():
            continue
        for root, _dirs, filenames in os.walk(pkg_path):
            root_path = pathlib.Path(root)
            for filename in filenames:
                filepath = root_path / filename
                arc_path = str(filepath.relative_to(parent)).replace(os.sep, "/")
                if arc_path in seen:
                    continue
                if filename.endswith((".py", ".pyi", ".css")) or filename == "py.typed":
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


def make_browser_webcompy_wheel(
    webcompy_package_dir: pathlib.Path,
    dest: pathlib.Path,
    version: str,
) -> pathlib.Path:
    wheel_path = make_wheel(
        "webcompy",
        webcompy_package_dir,
        dest,
        version,
    )
    return _content_hash_wheel(wheel_path, "webcompy", version)


def _content_hash_wheel(wheel_path: pathlib.Path, name: str, app_version: str) -> pathlib.Path:
    digest = hashlib.sha256(wheel_path.read_bytes()).hexdigest()[:8]
    hash_version = f"0+sha.{digest}"
    dist_name = _normalize_name(name)
    old_dist_info = f"{dist_name}-{app_version}.dist-info"
    new_dist_info = f"{dist_name}-{hash_version}.dist-info"
    new_filename = f"{_normalize_name(name)}-{hash_version}-py3-none-any.whl"

    with zipfile.ZipFile(wheel_path, "r") as zf_in:
        entries = []
        for info in zf_in.infolist():
            if info.filename == f"{old_dist_info}/RECORD":
                continue
            data = zf_in.read(info.filename)
            arc_path = info.filename
            if arc_path.startswith(old_dist_info + "/"):
                arc_path = new_dist_info + "/" + arc_path[len(old_dist_info) + 1 :]
            if arc_path == f"{new_dist_info}/METADATA":
                data = _write_metadata(name, hash_version).encode("utf-8")
            entries.append((arc_path, data))

    os.remove(wheel_path)
    new_path = wheel_path.parent / new_filename
    with zipfile.ZipFile(new_path, "w", zipfile.ZIP_DEFLATED) as zf_out:
        record_entries = []
        for arc_path, data in entries:
            _write_zip_entry(zf_out, arc_path, data)
            record_entries.append((arc_path, _sha256_b64(data), len(data)))
        record_content = _write_record(record_entries, new_dist_info)
        _write_zip_entry(zf_out, f"{new_dist_info}/RECORD", record_content)

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
            _write_zip_entry(zf, arc_path, data)
            record_entries.append((arc_path, _sha256_b64(data), len(data)))

        _write_zip_entry(zf, metadata_path, metadata_content)
        record_entries.append(
            (metadata_path, _sha256_b64(metadata_content.encode("utf-8")), len(metadata_content.encode("utf-8")))
        )
        _write_zip_entry(zf, wheel_meta_path, wheel_content)
        record_entries.append(
            (wheel_meta_path, _sha256_b64(wheel_content.encode("utf-8")), len(wheel_content.encode("utf-8")))
        )
        _write_zip_entry(zf, top_level_path, top_level_content)
        record_entries.append(
            (top_level_path, _sha256_b64(top_level_content.encode("utf-8")), len(top_level_content.encode("utf-8")))
        )

        record_content = _write_record(record_entries, dist_info)
        _write_zip_entry(zf, f"{dist_info}/RECORD", record_content)

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
            _write_zip_entry(zf, arc_path, data)
            record_entries.append((arc_path, _sha256_b64(data), len(data)))

        if extra_files:
            for arc_path, content in extra_files:
                _write_zip_entry(zf, arc_path, content)
                record_entries.append((arc_path, _sha256_b64(content), len(content)))

        _write_zip_entry(zf, metadata_path, metadata_content)
        record_entries.append(
            (metadata_path, _sha256_b64(metadata_content.encode("utf-8")), len(metadata_content.encode("utf-8")))
        )
        _write_zip_entry(zf, wheel_meta_path, wheel_content)
        record_entries.append(
            (wheel_meta_path, _sha256_b64(wheel_content.encode("utf-8")), len(wheel_content.encode("utf-8")))
        )
        _write_zip_entry(zf, top_level_path, top_level_content)
        record_entries.append(
            (top_level_path, _sha256_b64(top_level_content.encode("utf-8")), len(top_level_content.encode("utf-8")))
        )

        record_content = _write_record(record_entries, dist_info)
        _write_zip_entry(zf, f"{dist_info}/RECORD", record_content)

    return wheel_path


def make_webcompy_app_package(
    dest: pathlib.Path,
    webcompy_package_dir: pathlib.Path,
    package_dir: pathlib.Path,
    app_version: str,
    bundled_deps: list[tuple[str, pathlib.Path]] | None = None,
    skip_webcompy: bool = False,
) -> pathlib.Path:
    app_name = package_dir.name

    package_dirs: list[tuple[str, pathlib.Path]] = []
    if not skip_webcompy:
        package_dirs.append(("webcompy", webcompy_package_dir))
    package_dirs.append((app_name, package_dir))
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

    for _pkg_name, pkg_dir in package_dirs:
        packages = _discover_packages(pkg_dir)
        files = _collect_package_files(pkg_dir, packages, None)
        for filepath, arc_path in files:
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
            _write_zip_entry(zf, arc_path, data)
            record_entries.append((arc_path, _sha256_b64(data), len(data)))

        _write_zip_entry(zf, metadata_path, metadata_content)
        record_entries.append(
            (metadata_path, _sha256_b64(metadata_content.encode("utf-8")), len(metadata_content.encode("utf-8")))
        )
        _write_zip_entry(zf, wheel_meta_path, wheel_content)
        record_entries.append(
            (wheel_meta_path, _sha256_b64(wheel_content.encode("utf-8")), len(wheel_content.encode("utf-8")))
        )
        _write_zip_entry(zf, top_level_path, top_level_content)
        record_entries.append(
            (top_level_path, _sha256_b64(top_level_content.encode("utf-8")), len(top_level_content.encode("utf-8")))
        )

        record_content = _write_record(record_entries, dist_info)
        _write_zip_entry(zf, f"{dist_info}/RECORD", record_content)

    return _content_hash_wheel(wheel_path, app_name, app_version)
