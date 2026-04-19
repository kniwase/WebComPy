from __future__ import annotations

import warnings
from pathlib import Path


class WebComPyConfig:
    app_package_path: Path
    base: str
    server_port: int
    static_files_dir_path: Path
    dist: str
    dependencies: list[str]
    cname: str
    assets: dict[str, str] | None

    def __init__(
        self,
        app_package: Path | str,
        base: str = "/",
        server_port: int = 8080,
        static_files_dir: Path | str = "static",
        dist: str = "dist",
        dependencies: list[str] | None = None,
        cname: str = "",
        assets: dict[str, str] | None = None,
    ) -> None:
        warnings.warn(
            "WebComPyConfig is deprecated. Use AppConfig instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(app_package, Path):
            self.app_package_path = app_package.absolute()
        else:
            self.app_package_path = Path(f"./{app_package}").absolute()
        self.base = f"/{base}/" if (base := base.strip("/")) else "/"
        self.server_port = server_port
        if isinstance(static_files_dir, Path):
            self.static_files_dir_path = static_files_dir.absolute()
        else:
            self.static_files_dir_path = self.app_package_path.parent / static_files_dir
        self.dist = dist
        self.dependencies = [*dependencies] if dependencies else []
        self.cname = cname
        self.assets = assets
