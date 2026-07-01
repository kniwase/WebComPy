from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PluginScript:
    attrs: dict[str, str]
    script: str | None = None
    condition: str | None = None
    in_head: bool = False


_VALID_THEME_DEFAULTS = ("light", "dark", "system")


@dataclass
class WebComPyAppConfig:
    base_url: str = "/"
    selector: str = "#webcompy-app"
    profile: bool = False
    hydrate: bool = True
    scripts: list[PluginScript] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    theme: dict | None = None

    def __post_init__(self):
        stripped = self.base_url.strip("/")
        self.base_url = f"/{stripped}/" if stripped else "/"
        if self.theme is not None:
            self.theme = _normalize_theme_config(self.theme)


def _normalize_theme_config(theme: dict) -> dict:
    if not isinstance(theme, dict):
        raise TypeError(f"WebComPyAppConfig.theme must be a dict or None, got {type(theme).__name__}")
    normalized: dict = {}
    if "default" in theme:
        default = theme["default"]
        if default not in _VALID_THEME_DEFAULTS:
            raise ValueError(
                f"WebComPyAppConfig.theme['default'] must be one of {_VALID_THEME_DEFAULTS}, got {default!r}"
            )
        normalized["default"] = default
    else:
        normalized["default"] = "system"
    if "persist" in theme:
        persist = theme["persist"]
        if not isinstance(persist, bool):
            raise TypeError(f"WebComPyAppConfig.theme['persist'] must be a bool, got {type(persist).__name__}")
        normalized["persist"] = persist
    else:
        normalized["persist"] = True
    return normalized
