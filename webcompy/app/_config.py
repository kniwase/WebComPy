from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PluginScript:
    attrs: dict[str, str]
    script: str | None = None
    condition: str | None = None
    in_head: bool = False


@dataclass
class WebComPyAppConfig:
    base_url: str = "/"
    selector: str = "#webcompy-app"
    profile: bool = False
    hydrate: bool = True
    scripts: list[PluginScript] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)

    def __post_init__(self):
        stripped = self.base_url.strip("/")
        self.base_url = f"/{stripped}/" if stripped else "/"
