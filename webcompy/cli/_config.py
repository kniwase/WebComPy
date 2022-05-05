from dataclasses import dataclass

@dataclass
class WebComPyConfig:
    app_package: str
    base: str = "/"
    server_port: int = 8080
    dist: str = "dist"

    def __post_init__(self):
        self.base = f"/{base}" if (base := self.base.strip("/")) else "/"
