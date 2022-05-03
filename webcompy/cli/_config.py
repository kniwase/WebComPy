from dataclasses import dataclass, field
from typing import TypedDict


class Head(TypedDict, total=False):
    title: str
    meta: list[dict[str, str]]


@dataclass
class WebComPyConfig:
    app_package: str
    head: Head = field(default_factory=Head)
    base: str = "/"
    server_port: int = 8080
    ssr: bool = True
