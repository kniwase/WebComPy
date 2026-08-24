"""Starlette harness server that boots a real PyScript runtime for browser tests."""

from __future__ import annotations

import html as html_module
import json
import mimetypes
import os
import socket
import tempfile
import threading
import time
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import uvicorn
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Route

if TYPE_CHECKING:
    from starlette.requests import Request

from webcompy_cli._pyodide_downloader import download_pyodide_wheel
from webcompy_cli._pyodide_lock import fetch_pyodide_lock, get_pyodide_version
from webcompy_cli._runtime_downloader import download_runtime_assets
from webcompy_cli._utils import get_webcompy_packge_dir
from webcompy_cli._wheel_builder import make_browser_webcompy_wheel, make_wheel
from webcompy_server._html import PYSCRIPT_VERSION

SUPPLY_MODE_ENV_VAR = "WEBCOMPY_BROWSER_SOURCE"
BROWSER_TEST_DIR = "tests/browser"
_HARNESS_WHEEL_VERSION = "0+harness"
_HARNESS_PYODIDE_PACKAGES: tuple[str, ...] = ("micropip", "httpx", "starlette", "anyio")
_WC_SRC_MOUNT_ROOT = "/home/pyodide/_wc_src"
_TESTS_MOUNT_PARENT = "/home/pyodide"
_FRAMEWORK_TREES: dict[str, str] = {
    "webcompy": "packages/webcompy/src/webcompy",
    "webcompy_testing": "packages/webcompy-testing/src/webcompy_testing",
    "webcompy_server": "packages/webcompy-server/src/webcompy_server",
}
_MOUNTED_TREE_BASES: dict[str, str] = {
    "tests": "tests",
    "webcompy": "packages/webcompy/src",
    "webcompy_testing": "packages/webcompy-testing/src",
    "webcompy_server": "packages/webcompy-server/src",
}
_BOOT_TIMEOUT_SECONDS = 30.0

ConsoleCollectorJS = (
    "window.__webcompy_test_console__=[];"
    "(function(){var b=window.__webcompy_test_console__,o=console.error;"
    'console.error=function(){b.push({type:"error",'
    "text:Array.prototype.slice.call(arguments).map(String).join(' ')});"
    "o.apply(console,arguments)};"
    'window.addEventListener("error",function(e){'
    'b.push({type:"error",text:"uncaught: "+e.message})});})();'
)


def resolve_supply_mode() -> Literal["wheel", "source"]:
    """Return the framework supply mode selected by ``WEBCOMPY_BROWSER_SOURCE``."""
    if os.environ.get(SUPPLY_MODE_ENV_VAR) == "1":
        return "source"
    return "wheel"


def discover_test_modules(repo_root: Path) -> list[Path]:
    """Return sorted repo-relative paths of test modules under ``tests/browser``."""
    base = repo_root / BROWSER_TEST_DIR
    if not base.is_dir():
        return []
    return sorted(p.relative_to(repo_root) for p in base.rglob("test_*.py") if p.is_file())


def collect_framework_source_files(repo_root: Path) -> dict[str, list[str]]:
    """Map each framework package name to sorted POSIX paths under its ``src`` root."""
    result: dict[str, list[str]] = {}
    for pkg_name, tree_rel in _FRAMEWORK_TREES.items():
        src_root = (repo_root / tree_rel).parent
        result[pkg_name] = [
            p.relative_to(src_root).as_posix()
            for p in sorted(src_root.rglob("*.py"))
            if p.is_file() and "__pycache__" not in p.parts
        ]
    return result


def build_py_config(
    *,
    base_url: str,
    supply_mode: Literal["wheel", "source"],
    wheel_names: list[str],
    test_relpaths: list[str],
    framework_files: dict[str, list[str]] | None = None,
    pyodide_package_names: tuple[str, ...] = _HARNESS_PYODIDE_PACKAGES,
) -> dict:
    """Generate the harness py-config dictionary with parity to ``webcompy_server._html``."""
    normalized = base_url.rstrip("/")
    config: dict = {"experimental_create_proxy": "auto"}
    files: dict[str, str] = {}
    for rel in test_relpaths:
        files[f"{normalized}/_webcompy-test/files/{rel}"] = f"{_TESTS_MOUNT_PARENT}/{rel}"
    wheel_urls = [f"{normalized}/_webcompy-test/wheels/{name}" for name in wheel_names]
    if supply_mode == "wheel":
        config["packages"] = [*pyodide_package_names, *wheel_urls]
    elif framework_files is not None:
        for pkg_name, rels in framework_files.items():
            for rel in rels:
                files[f"{normalized}/_webcompy-test/files/{pkg_name}/{rel}"] = f"{_WC_SRC_MOUNT_ROOT}/{rel}"
        config["packages"] = list(pyodide_package_names)
    if files:
        config["files"] = files
    config["interpreter"] = f"{normalized}/_webcompy-assets/pyodide/pyodide.mjs"
    config["lockFileURL"] = f"{normalized}/_webcompy-assets/pyodide/pyodide-lock.json"
    return config


def bootstrap_lines(supply_mode: Literal["wheel", "source"]) -> str:
    """Return the inline ``<script type=\"py\">`` lines that boot the in-page runner."""
    lines = ["import sys"]
    if supply_mode == "source":
        lines.append(f'sys.path.insert(0, "{_WC_SRC_MOUNT_ROOT}")')
    lines.append(f'sys.path.insert(0, "{_TESTS_MOUNT_PARENT}")')
    lines.append("from webcompy_testing.browser_runner import bootstrap")
    lines.append("bootstrap()")
    return "\n".join(lines)


def generate_harness_html(
    py_config: dict,
    *,
    base_url: str,
    source_mounted: bool,
) -> str:
    """Render the harness page that boots PyScript with the given py-config."""
    normalized = base_url.rstrip("/")
    config_attr = html_module.escape(json.dumps(py_config), quote=True)
    bootstrap = bootstrap_lines("source" if source_mounted else "wheel")
    return (
        "<!doctype html>"
        "<html>"
        "<head>"
        f'<link rel="stylesheet" href="{normalized}/_webcompy-assets/core.css">'
        f'<script type="module" src="{normalized}/_webcompy-assets/core.js"></script>'
        "</head>"
        "<body>"
        '<div id="webcompy-app"></div>'
        f"<script>{ConsoleCollectorJS}</script>"
        f'<script type="py" config="{config_attr}">\n{bootstrap}\n</script>'
        "</body>"
        "</html>"
    )


def _asset_media_type(filename: str) -> str:
    if filename.endswith((".js", ".mjs")):
        return "text/javascript"
    if filename.endswith(".css"):
        return "text/css"
    if filename.endswith(".json"):
        return "application/json"
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def _build_harness_wheels() -> dict[str, bytes]:
    """Build the three framework wheels and read their bytes into memory."""
    testing_pkg = Path(import_module("webcompy_testing").__file__).parent  # type: ignore[arg-type]
    server_pkg = Path(import_module("webcompy_server").__file__).parent  # type: ignore[arg-type]
    wheels: dict[str, bytes] = {}
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        built = [
            make_browser_webcompy_wheel(get_webcompy_packge_dir(), dest, _HARNESS_WHEEL_VERSION),
            make_wheel("webcompy_testing", testing_pkg, dest, _HARNESS_WHEEL_VERSION),
            make_wheel("webcompy_server", server_pkg, dest, _HARNESS_WHEEL_VERSION),
        ]
        for wheel_path in built:
            wheels[wheel_path.name] = wheel_path.read_bytes()
    return wheels


def resolve_pyodide_package_closure(
    pyodide_version: str,
    cache_dir: Path,
    *,
    package_names: tuple[str, ...],
) -> tuple[str, ...]:
    """Expand seed package names to their transitive dependency closure per the lock."""
    pyodide_lock = fetch_pyodide_lock(pyodide_version, cache_dir)
    packages = pyodide_lock.get("packages", {})
    pending = list(package_names)
    seen: set[str] = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        info = packages.get(name)
        if info is None:
            continue
        pending.extend(info.get("depends", []))
    return tuple(sorted(seen))


def _pure_python_installable(info: dict) -> bool:
    """Whether micropip can install this lock entry by name (pure Python wheel)."""
    file_name = info.get("file_name", "")
    return file_name.endswith("py3-none-any.whl")


def _installable_pyodide_packages(
    cache_dir: Path,
    pyodide_version: str,
    closure: tuple[str, ...],
) -> tuple[str, ...]:
    """Filter a package closure to entries installable by name via micropip."""
    packages = fetch_pyodide_lock(pyodide_version, cache_dir).get("packages", {})
    return tuple(
        name for name in closure if (info := packages.get(name)) is not None and _pure_python_installable(info)
    )


def _ensure_pyodide_package_files(
    runtime_assets: dict[str, tuple[Path, str]],
    pyodide_version: str,
    cache_dir: Path,
    *,
    package_names: tuple[str, ...],
) -> None:
    """Fetch the Pyodide-distribution wheels needed by the harness page locally.

    ``micropip`` installs URL packages, while the framework's import chain
    (``webcompy_testing`` -> ``webcompy_server.ports`` -> ``httpx`` /
    ``starlette``) needs its third-party imports present in the interpreter.
    ``package_names`` must already be a resolved dependency closure.
    """
    packages = fetch_pyodide_lock(pyodide_version, cache_dir).get("packages", {})
    dest_dir = cache_dir / "runtime-assets" / PYSCRIPT_VERSION / "pyodide"
    for name in package_names:
        info = packages.get(name)
        if info is None:
            continue
        file_name = info.get("file_name")
        sha256 = info.get("sha256")
        if not file_name or not sha256:
            continue
        rel_key = f"pyodide/{file_name}"
        if rel_key in runtime_assets:
            continue
        try:
            wheel_path = download_pyodide_wheel(file_name, pyodide_version, sha256, cache_dir)
        except Exception as e:
            print(f"Warning: failed to fetch pyodide package {name}: {e}", flush=True)
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / file_name
        if dest != wheel_path:
            dest.write_bytes(wheel_path.read_bytes())
        runtime_assets[rel_key] = (dest, sha256)


@dataclass
class HarnessServer:
    """Harness Starlette application plus the metadata drivers need."""

    asgi: Starlette
    py_config: dict
    manifest_modules: list[str]
    supply_mode: Literal["wheel", "source"]
    wheel_filenames: list[str] = field(default_factory=list)


def create_harness_app(
    repo_root: Path,
    cache_dir: Path,
    *,
    base_url: str,
    supply_mode: Literal["wheel", "source"] | None = None,
) -> HarnessServer:
    """Assemble the harness application serving assets, files, config, manifest, and page."""
    mode = supply_mode or resolve_supply_mode()
    print(
        f"[webcompy-browser-harness] preparing runtime assets ({mode} mode)...",
        flush=True,
    )
    pyodide_version = get_pyodide_version(PYSCRIPT_VERSION)
    runtime_assets = download_runtime_assets(
        pyodide_version,
        PYSCRIPT_VERSION,
        cache_dir,
    )
    package_closure = resolve_pyodide_package_closure(
        pyodide_version,
        cache_dir,
        package_names=_HARNESS_PYODIDE_PACKAGES,
    )
    installable = _installable_pyodide_packages(cache_dir, pyodide_version, package_closure)
    _ensure_pyodide_package_files(
        runtime_assets,
        pyodide_version,
        cache_dir,
        package_names=package_closure,
    )
    test_paths = discover_test_modules(repo_root)
    test_rels = [p.as_posix() for p in test_paths]
    manifest_modules = [rel[: -len(".py")].replace("/", ".") for rel in test_rels]

    wheel_names: list[str] = []
    framework_files: dict[str, list[str]] | None = None
    wheel_bytes: dict[str, bytes] = {}
    if mode == "wheel":
        wheel_bytes = _build_harness_wheels()
        wheel_names = sorted(wheel_bytes)
    else:
        framework_files = collect_framework_source_files(repo_root)

    py_config = build_py_config(
        base_url=base_url,
        supply_mode=mode,
        wheel_names=wheel_names,
        test_relpaths=test_rels,
        framework_files=framework_files,
        pyodide_package_names=installable,
    )
    harness_html = generate_harness_html(
        py_config,
        base_url=base_url,
        source_mounted=mode == "source",
    )

    async def send_runtime_asset(request: Request):
        filename: str = request.path_params.get("filename", "")  # type: ignore[assignment]
        entry = runtime_assets.get(filename)
        if entry is None:
            raise HTTPException(404)
        return FileResponse(entry[0], media_type=_asset_media_type(filename))

    async def send_mounted_file(request: Request):
        tree: str = request.path_params.get("tree", "")  # type: ignore[assignment]
        rel: str = request.path_params.get("path", "")  # type: ignore[assignment]
        tree_base = _MOUNTED_TREE_BASES.get(tree)
        if tree_base is None or not rel:
            raise HTTPException(404)
        base_dir = (repo_root / tree_base).resolve()
        target = (base_dir / rel).resolve()
        try:
            target.relative_to(base_dir)
        except ValueError:
            raise HTTPException(403) from None
        if not target.is_file():
            raise HTTPException(404)
        return FileResponse(target, media_type=_asset_media_type(target.name))

    async def send_wheel(request: Request):
        filename: str = request.path_params.get("filename", "")  # type: ignore[assignment]
        content = wheel_bytes.get(filename)
        if content is None:
            raise HTTPException(404)
        return Response(content, media_type="application/zip")

    async def send_config(request: Request):
        return JSONResponse(py_config)

    async def send_manifest(request: Request):
        return JSONResponse({"modules": manifest_modules})

    async def send_testharness(request: Request):
        return Response(harness_html, media_type="text/html")

    routes = [
        Route("/_webcompy-assets/{filename:path}", send_runtime_asset),
        Route("/_webcompy-test/files/{tree}/{path:path}", send_mounted_file),
        Route("/_webcompy-test/wheels/{filename}", send_wheel),
        Route("/_webcompy-test/config.json", send_config),
        Route("/_webcompy-test/manifest.json", send_manifest),
        Route("/testharness", send_testharness),
    ]
    return HarnessServer(
        asgi=Starlette(routes=routes),
        py_config=py_config,
        manifest_modules=manifest_modules,
        supply_mode=mode,
        wheel_filenames=wheel_names,
    )


@dataclass
class HarnessProcess:
    """A running harness server bound to an ephemeral local port."""

    server: uvicorn.Server
    thread: threading.Thread
    port: int


def reserve_port(host: str = "127.0.0.1") -> int:
    """Reserve an ephemeral TCP port by binding and immediately releasing it."""
    probe = socket.socket()
    probe.bind((host, 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


def serve_harness(
    harness: HarnessServer,
    *,
    host: str = "127.0.0.1",
    port: int | None = None,
) -> HarnessProcess:
    """Run the harness ASGI app with uvicorn in a daemon thread."""
    if port is None:
        port = reserve_port(host)
    config = uvicorn.Config(harness.asgi, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + _BOOT_TIMEOUT_SECONDS
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("Harness server failed to start within the timeout.")
        time.sleep(0.05)
    return HarnessProcess(server=server, thread=thread, port=port)


def shutdown_harness(process: HarnessProcess) -> None:
    """Stop the harness server thread."""
    process.server.should_exit = True
    process.thread.join(timeout=5)
