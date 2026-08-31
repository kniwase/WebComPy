"""Build configuration for WebComPy projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Literal

from webcompy_cli.config._pwa_config import PWAConfig
from webcompy_cli.config._server_config import LockfileSyncConfig, WebComPyServerConfig


class _Sentinel:
    pass


_UNSET: _Sentinel = _Sentinel()


@dataclass
class WebComPyBuildConfig:
    """Build configuration for a WebComPy application package.

    Collects all options controlling dependency resolution, wheel
    building, resource handling, and serving. ``app_package_path`` and
    ``app`` are derived from ``app_module``/``app_var`` in
    ``__post_init__``.

    Args:
        app_module: Python module containing the application instance.
        app_var: Attribute name of the application inside ``app_module``.
        dependencies: Explicit browser dependency names, or ``None`` to
            discover from ``pyproject.toml``.
        dependencies_from: Optional dependency group name in
            ``pyproject.toml`` to resolve ``dependencies`` from.
        resources: Glob patterns selecting resource files, or ``None`` for
            the default includes. An empty list disables resources.
        resource_exclude: Glob patterns excluding resource files.
        version: Application version string, or ``None`` for ``"0.0.0"``.
        serve_all_deps: Whether to bundle all pure-Python dependencies
            into the app wheel.
        wasm_serving: How WASM packages are served, or ``None`` to
            resolve from ``standalone``.
        runtime_serving: How the PyScript/Pyodide runtime is served, or
            ``None`` to resolve from ``standalone``.
        standalone: Whether to serve all assets locally.
        wheel_mode: Wheel bundling mode.
        resource_transfer: How resource files are transferred to the
            browser.
        dist: Output directory for the static site.
        cname: Value written to the ``CNAME`` file, when any.
        static_files_dir: Directory housing static files relative to the
            app package path.
        lockfile_sync_config: Configuration for lock file synchronization.
        server: Server configuration.
        pwa: Progressive Web App build configuration.

    Attributes:
        app_module: Python module containing the application instance.
        app_var: Attribute name of the application inside ``app_module``.
        app: The application instance resolved from ``app_module``/
            ``app_var``.
        app_package_path: Directory containing the application package,
            derived from ``app_module``.
        dependencies: Explicit browser dependency names, or ``None`` to
            discover from ``pyproject.toml``.
        dependencies_from: Optional dependency group name in
            ``pyproject.toml`` to resolve ``dependencies`` from.
        resources: Glob patterns selecting resource files, or ``None`` for
            the default includes.
        resource_exclude: Glob patterns excluding resource files.
        version: Application version string, or ``None`` for ``"0.0.0"``.
        serve_all_deps: Whether to bundle all pure-Python dependencies
            into the app wheel.
        wasm_serving: How WASM packages are served.
        runtime_serving: How the PyScript/Pyodide runtime is served.
        standalone: Whether to serve all assets locally.
        wheel_mode: Wheel bundling mode.
        resource_transfer: How resource files are transferred.
        dist: Output directory for the static site.
        cname: Value written to the ``CNAME`` file, when any.
        static_files_dir: Directory housing static files.
        lockfile_sync_config: Configuration for lock file synchronization.
        server: Server configuration.
        pwa: Progressive Web App build configuration.

    """

    app_module: ModuleType
    app_var: str = "app"
    dependencies: list[str] | None = None
    dependencies_from: str | None = None
    resources: list[str] | None = None
    resource_exclude: list[str] | None = None
    version: str | None = None
    serve_all_deps: bool = True
    wasm_serving: Literal["cdn", "local"] | None = None
    runtime_serving: Literal["cdn", "local"] | None = None
    standalone: bool = False
    wheel_mode: Literal["bundled", "split"] = "bundled"
    resource_transfer: Literal["used", "all-text"] = "used"
    dist: str = "dist"
    cname: str = ""
    static_files_dir: str = "static"
    lockfile_sync_config: LockfileSyncConfig | None = None
    server: WebComPyServerConfig = field(default_factory=WebComPyServerConfig)
    pwa: PWAConfig = field(default_factory=PWAConfig)

    def __post_init__(self):
        if self.resource_transfer not in ("used", "all-text"):
            from webcompy.exception import WebComPyException

            raise WebComPyException(
                f"Invalid resource_transfer: {self.resource_transfer!r}. Valid values: 'used', 'all-text'"
            )
        self.app_package_path = Path(self.app_module.__file__).parent  # type: ignore[arg-type]
        self.app = getattr(self.app_module, self.app_var)
        self._explicit_wasm_serving: Literal["cdn", "local"] | _Sentinel = (
            self.wasm_serving if self.wasm_serving is not None else _UNSET
        )
        self._explicit_runtime_serving: Literal["cdn", "local"] | _Sentinel = (
            self.runtime_serving if self.runtime_serving is not None else _UNSET
        )
        self.resolve_standalone()

    def resolve_standalone(self):
        """Resolve implicit serving modes from the ``standalone`` flag."""

        if self.standalone:
            import sys

            if self.serve_all_deps is False:
                print("Warning: standalone=True forces serve_all_deps=True", file=sys.stderr, flush=True)
            self.serve_all_deps = True
            self.wasm_serving = (
                "local" if isinstance(self._explicit_wasm_serving, _Sentinel) else self._explicit_wasm_serving
            )
            self.runtime_serving = (
                "local" if isinstance(self._explicit_runtime_serving, _Sentinel) else self._explicit_runtime_serving
            )
        else:
            self.wasm_serving = (
                "cdn" if isinstance(self._explicit_wasm_serving, _Sentinel) else self._explicit_wasm_serving
            )
            self.runtime_serving = (
                "cdn" if isinstance(self._explicit_runtime_serving, _Sentinel) else self._explicit_runtime_serving
            )
