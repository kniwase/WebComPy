from dataclasses import dataclass, field
from typing import Literal

@dataclass
class WebComPyConfig:
    app_package: str
    base: str = "/"
    server_port: int = 8080
    dist: str = "dist"
    dependencies: list[str] = field(default_factory=list)
    environment: Literal["pyscript", "brython"] = "pyscript"

    def __post_init__(self):
        self.base = f"/{base}/" if (base := self.base.strip("/")) else "/"
