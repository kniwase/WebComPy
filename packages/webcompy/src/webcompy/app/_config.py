from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginScript:
    attrs: dict[str, str]
    script: str | None = None
    condition: str | None = None
    in_head: bool = False


_VALID_THEME_DEFAULTS = ("light", "dark", "system")

_LOADING_STAGE_KEYS = (
    "runtime_prepare",
    "runtime_download",
    "packages",
    "runtime_ready",
    "app_start",
)

_LOADING_MODES = ("auto", "overlay", "content")
_LOADING_INTERACTIONS = ("block", "inert", "passthrough")
_LOADING_DEFAULTS: dict = {
    "mode": "auto",
    "interaction": "block",
    "stages": True,
    "dormant": True,
    "messages": {},
    "template": None,
    "reveal_delay_ms": 350,
    "fade_out_ms": 250,
    "timeout_seconds": 30,
}


@dataclass
class WebComPyAppConfig:
    base_url: str = "/"
    selector: str = "#webcompy-app"
    profile: bool = False
    hydrate: bool = True
    scroll_restoration: bool = True
    scripts: list[PluginScript] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    theme: dict | None = None
    loading: dict | None = None
    compression_threshold: int | None = 1024
    on_error: Callable[[Exception], Any] | None = None

    def __post_init__(self):
        stripped = self.base_url.strip("/")
        self.base_url = f"/{stripped}/" if stripped else "/"
        if self.theme is not None:
            self.theme = _normalize_theme_config(self.theme)
        if self.loading is not None:
            self.loading = _normalize_loading_config(self.loading)


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


def _normalize_loading_config(loading: dict) -> dict:
    if not isinstance(loading, dict):
        raise TypeError(f"WebComPyAppConfig.loading must be a dict or None, got {type(loading).__name__}")
    unknown = set(loading) - set(_LOADING_DEFAULTS)
    if unknown:
        raise ValueError(f"WebComPyAppConfig.loading contains unknown keys: {sorted(unknown)}")
    normalized = dict(_LOADING_DEFAULTS)
    for key, value in loading.items():
        if key == "mode":
            if value not in _LOADING_MODES:
                raise ValueError(f"WebComPyAppConfig.loading['mode'] must be one of {_LOADING_MODES}, got {value!r}")
        elif key == "interaction":
            if value not in _LOADING_INTERACTIONS:
                raise ValueError(
                    f"WebComPyAppConfig.loading['interaction'] must be one of {_LOADING_INTERACTIONS}, got {value!r}"
                )
        elif key in ("stages", "dormant"):
            if not isinstance(value, bool):
                raise TypeError(f"WebComPyAppConfig.loading['{key}'] must be a bool, got {type(value).__name__}")
        elif key == "messages":
            if not isinstance(value, dict):
                raise TypeError(f"WebComPyAppConfig.loading['messages'] must be a dict, got {type(value).__name__}")
            bad = sorted(set(value) - set(_LOADING_STAGE_KEYS))
            if bad:
                raise ValueError(
                    f"WebComPyAppConfig.loading['messages'] contains unknown stage keys: {bad}. "
                    f"Valid keys: {_LOADING_STAGE_KEYS}"
                )
            normalized["messages"] = dict(value)
            continue
        elif key == "template":
            if value is not None and not isinstance(value, str):
                raise TypeError(
                    f"WebComPyAppConfig.loading['template'] must be a str or None, got {type(value).__name__}"
                )
        elif key in ("reveal_delay_ms", "fade_out_ms", "timeout_seconds"):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"WebComPyAppConfig.loading['{key}'] must be an int, got {type(value).__name__}")
            if value < 0:
                raise ValueError(f"WebComPyAppConfig.loading['{key}'] must be a non-negative int, got {value!r}")
        normalized[key] = value
    return normalized
