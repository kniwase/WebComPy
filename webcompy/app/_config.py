from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class AppConfig:
    app_package: Path | str = "."
    base_url: str = "/"
    dependencies: list[str] | None = None
    dependencies_from: str | None = None
    assets: dict[str, str] | None = None
    version: str | None = None
    profile: bool = False
    hydrate: bool = True
    serve_all_deps: bool = True
    wasm_serving: Literal["cdn", "local"] | None = None
    runtime_serving: Literal["cdn", "local"] | None = None

    def __post_init__(self):
        stripped = self.base_url.strip("/")
        self.base_url = f"/{stripped}/" if stripped else "/"
        if isinstance(self.app_package, Path):
            self.app_package_path = self.app_package.absolute()
        else:
            self.app_package_path = Path(f"./{self.app_package}").absolute()


@dataclass
class ServerConfig:
    port: int = 8080
    dev: bool = False
    static_files_dir: str = "static"
    lockfile_sync_config: LockfileSyncConfig | None = None

    @property
    def static_files_dir_path(self) -> Path:
        return Path(self.static_files_dir).absolute()


@dataclass
class GenerateConfig:
    dist: str = "dist"
    cname: str = ""
    static_files_dir: str = "static"
    lockfile_sync_config: LockfileSyncConfig | None = None

    @property
    def static_files_dir_path(self) -> Path:
        return Path(self.static_files_dir).absolute()


@dataclass
class LockfileSyncConfig:
    requirements_path: str | None = None
    sync_group: str | None = None
