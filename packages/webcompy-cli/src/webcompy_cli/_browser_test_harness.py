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

from webcompy_cli._pyodide_lock import get_pyodide_version
from webcompy_cli._runtime_downloader import download_runtime_assets
from webcompy_cli._utils import get_webcompy_packge_dir
from webcompy_cli._wheel_builder import make_browser_webcompy_wheel, make_wheel
from webcompy_server._html import PYSCRIPT_VERSION

SUPPLY_MODE_ENV_VAR = "WEBCOMPY_BROWSER_SOURCE"
BROWSER_TEST_DIR = "tests/browser"
_HARNESS_WHEEL_VERSION = "0+harness"
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
) -> dict:
    """Generate the harness py-config dictionary with parity to ``webcompy_server._html``."""
    normalized = base_url.rstrip("/")
    config: dict = {"experimental_create_proxy": "auto"}
    files: dict[str, str] = {}
    for rel in test_relpaths:
        files[f"{normalized}/_webcompy-test/files/{rel}"] = f"{_TESTS_MOUNT_PARENT}/{rel}"
    if supply_mode == "wheel":
        config["packages"] = [f"{normalized}/_webcompy-test/wheels/{name}" for name in wheel_names]
    elif framework_files is not None:
        for pkg_name, rels in framework_files.items():
            for rel in rels:
                files[f"{normalized}/_webcompy-test/files/{pkg_name}/{rel}"] = f"{_WC_SRC_MOUNT_ROOT}/{rel}"
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
    runtime_assets = download_runtime_assets(
        get_pyodide_version(PYSCRIPT_VERSION),
        PYSCRIPT_VERSION,
        cache_dir,
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


def serve_harness(harness: HarnessServer, *, host: str = "127.0.0.1") -> HarnessProcess:
    """Run the harness ASGI app with uvicorn in a daemon thread on a free port."""
    probe = socket.socket()
    probe.bind((host, 0))
    port = probe.getsockname()[1]
    probe.close()
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
