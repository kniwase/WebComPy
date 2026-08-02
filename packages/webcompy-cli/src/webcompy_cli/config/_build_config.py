from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Literal

from webcompy_cli.config._server_config import LockfileSyncConfig, WebComPyServerConfig


class _Sentinel:
    pass


_UNSET: _Sentinel = _Sentinel()


@dataclass
class WebComPyBuildConfig:
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
    dist: str = "dist"
    cname: str = ""
    static_files_dir: str = "static"
    lockfile_sync_config: LockfileSyncConfig | None = None
    server: WebComPyServerConfig = field(default_factory=WebComPyServerConfig)

    def __post_init__(self):
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
