"""Configuration dataclasses for build and server settings."""

from webcompy_cli.config._build_config import WebComPyBuildConfig
from webcompy_cli.config._pwa_config import (
    ManifestConfig,
    ManifestIcon,
    PWAConfig,
    RuntimeCachingRule,
    RuntimeCachingStrategy,
)
from webcompy_cli.config._server_config import LockfileSyncConfig, WebComPyServerConfig

__all__ = [
    "LockfileSyncConfig",
    "ManifestConfig",
    "ManifestIcon",
    "PWAConfig",
    "RuntimeCachingRule",
    "RuntimeCachingStrategy",
    "WebComPyBuildConfig",
    "WebComPyServerConfig",
]
