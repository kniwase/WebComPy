"""Progressive Web App configuration dataclasses for build-time generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Literal, TypeAlias

from webcompy.exception import WebComPyException

RuntimeCachingStrategy: TypeAlias = Literal["cache-first", "network-first", "stale-while-revalidate"]
"""Caching strategy applied to requests matching a runtime caching rule."""

_VALID_STRATEGIES = ("cache-first", "network-first", "stale-while-revalidate")
_VALID_PRECACHE_MODES = ("auto", "none")
_VALID_DISPLAYS = ("fullscreen", "standalone", "minimal-ui", "browser")


@dataclass
class ManifestIcon:
    """An icon entry in the Web App Manifest.

    Args:
        src: URL of the icon, resolved relative to the application base
            URL. Typically a path inside the static files directory.
        sizes: Space-separated icon sizes (e.g. ``"192x192 512x512"``).
        type: Optional MIME type of the icon resource.
        purpose: Optional icon purpose (e.g. ``"maskable"``).

    Attributes:
        src: URL of the icon, resolved relative to the application base URL.
        sizes: Space-separated icon sizes.
        type: Optional MIME type of the icon resource.
        purpose: Optional icon purpose.

    """

    src: str
    sizes: str
    type: str | None = None
    purpose: str | None = None


@dataclass
class ManifestConfig:
    """Web App Manifest metadata serialized to ``manifest.webmanifest``.

    Args:
        name: Human-readable application name.
        short_name: Optional shortened name for launchers.
        icons: Icon entries referenced by the manifest.
        display: Display mode; one of ``fullscreen``, ``standalone``,
            ``minimal-ui`` or ``browser``.
        theme_color: Optional default theme color.
        background_color: Optional splash background color.
        start_url: Optional start URL; defaults to the app base URL.
        scope: Optional navigation scope; defaults to the app base URL.

    Attributes:
        name: Human-readable application name.
        short_name: Optional shortened name for launchers.
        icons: Icon entries referenced by the manifest.
        display: Display mode.
        theme_color: Optional default theme color.
        background_color: Optional splash background color.
        start_url: Optional start URL; defaults to the app base URL.
        scope: Optional navigation scope; defaults to the app base URL.

    """

    name: str
    short_name: str | None = None
    icons: list[ManifestIcon] = field(default_factory=list)
    display: str = "standalone"
    theme_color: str | None = None
    background_color: str | None = None
    start_url: str | None = None
    scope: str | None = None


@dataclass
class RuntimeCachingRule:
    """A runtime caching rule matched against same-origin requests.

    Args:
        pattern: Same-origin URL pattern; a path prefix or a glob with
            ``*`` (single segment) and ``**`` (any depth).
        strategy: Caching strategy applied to matching requests; one of
            ``cache-first``, ``network-first`` or
            ``stale-while-revalidate``.
        max_entries: Optional maximum number of entries kept in the rule's
            cache before eviction trims it.
        max_age: Optional maximum cached entry age in seconds; enforced
            best-effort within a worker lifetime.

    Attributes:
        pattern: Same-origin URL pattern.
        strategy: Caching strategy applied to matching requests.
        max_entries: Optional maximum number of cached entries.
        max_age: Optional maximum cached entry age in seconds.

    """

    pattern: str
    strategy: RuntimeCachingStrategy
    max_entries: int | None = None
    max_age: int | None = None


@dataclass
class PWAConfig:
    """Progressive Web App build configuration (disabled by default).

    Args:
        enabled: Whether PWA support is active; defaults to ``False``.
        manifest: Manifest metadata; required when ``enabled`` is true.
        precache: Precache mode, ``"auto"`` (enumerate build output) or
            ``"none"`` (empty precache manifest).
        precache_runtime: Opt-in to precaching the Python runtime files,
            which logs a build-time size warning.
        runtime: Runtime caching rules applied to same-origin requests.
        fallback_path: Optional path (relative to the static files
            directory) of an offline fallback page overriding the
            framework default.

    Attributes:
        enabled: Whether PWA support is active.
        manifest: Manifest metadata; ``None`` when not configured.
        precache: Precache mode (``"auto"`` or ``"none"``).
        precache_runtime: Whether the Python runtime is precached.
        runtime: Runtime caching rules.
        fallback_path: Optional offline fallback page path.

    """

    enabled: bool = False
    manifest: ManifestConfig | None = None
    precache: Literal["auto", "none"] = "auto"
    precache_runtime: bool = False
    runtime: list[RuntimeCachingRule] = field(default_factory=list)
    fallback_path: str | None = None

    def validate(self, *, app_package_path: Path, static_files_dir: str) -> None:
        """Validate this configuration at build start.

        A no-op when PWA is disabled. Called by the build pipeline before
        artifacts are resolved so errors surface with actionable messages.

        Args:
            app_package_path: Filesystem path of the application package,
                used to resolve the static files directory.
            static_files_dir: Static files directory relative to the
                application package path.

        Raises:
            WebComPyException: If any configured value is invalid or an
                inconsistent combination is used.

        """
        if not self.enabled:
            return
        if self.manifest is None:
            raise WebComPyException("PWAConfig.enabled is True but no manifest is configured: set PWAConfig.manifest")
        if self.precache not in _VALID_PRECACHE_MODES:
            raise WebComPyException(
                f"Invalid PWAConfig.precache: {self.precache!r}. Valid values: {_VALID_PRECACHE_MODES}"
            )
        if self.precache == "none" and self.precache_runtime:
            raise WebComPyException(
                "PWAConfig.precache_runtime cannot be enabled with precache='none': there is no precache to add runtime files to"
            )
        if self.manifest.display not in _VALID_DISPLAYS:
            raise WebComPyException(
                f"Invalid ManifestConfig.display: {self.manifest.display!r}. Valid values: {_VALID_DISPLAYS}"
            )
        for index, rule in enumerate(self.runtime):
            label = f"PWAConfig.runtime[{index}]"
            if not rule.pattern:
                raise WebComPyException(f"{label}.pattern must be a non-empty path prefix or glob")
            if "://" in rule.pattern:
                raise WebComPyException(f"{label}.pattern must be a same-origin path pattern, got {rule.pattern!r}")
            if rule.strategy not in _VALID_STRATEGIES:
                raise WebComPyException(
                    f"{label}.strategy is invalid: {rule.strategy!r}. Valid values: {_VALID_STRATEGIES}"
                )
            for key in ("max_entries", "max_age"):
                value = getattr(rule, key)
                if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value <= 0):
                    raise WebComPyException(f"{label}.{key} must be a positive int or None, got {value!r}")
        if self.fallback_path is not None:
            fallback = PurePosixPath(self.fallback_path)
            if fallback.is_absolute() or ".." in fallback.parts or not str(fallback):
                raise WebComPyException(
                    f"PWAConfig.fallback_path must be a relative path inside the static files directory, got {self.fallback_path!r}"
                )
            static_dir = app_package_path / static_files_dir
            candidate = static_dir.joinpath(*fallback.parts)
            if not candidate.is_file():
                raise WebComPyException(f"PWAConfig.fallback_path does not exist: {candidate}")
