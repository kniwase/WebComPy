"""Build-time Progressive Web App generation: manifest serialization, precache enumeration, and worker emission.

The framework owns the Service Worker implementation as a vanilla JS
template embedded in this module; the effective PWA configuration is
serialized into it at build time so the worker operates offline from its
first install without fetching any runtime configuration.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

from webcompy.exception import WebComPyException

if TYPE_CHECKING:
    from webcompy_cli.config._pwa_config import PWAConfig

MANIFEST_FILENAME = "manifest.webmanifest"
SW_FILENAME = "sw.js"
PWA_OUTPUT_NAMES = frozenset({MANIFEST_FILENAME, SW_FILENAME})
MANIFEST_MEDIA_TYPE = "application/manifest+json"
SW_MEDIA_TYPE = "application/javascript"


def serialize_manifest(pwa: PWAConfig, base_url: str) -> str:
    """Serialize the PWA manifest configuration to Web App Manifest JSON.

    Args:
        pwa: PWA configuration whose ``manifest`` is serialized.
        base_url: Application base URL (normalized with surrounding
            slashes) used for ``start_url`` and ``scope`` defaults.

    Returns:
        The ``manifest.webmanifest`` document as a JSON string.

    Raises:
        WebComPyException: If no manifest is configured.

    """
    manifest = pwa.manifest
    if manifest is None:
        raise WebComPyException("serialize_manifest requires PWAConfig.manifest to be set")
    data: dict = {
        "name": manifest.name,
        "start_url": base_url if manifest.start_url is None else manifest.start_url,
        "scope": base_url if manifest.scope is None else manifest.scope,
        "display": manifest.display,
    }
    if manifest.short_name is not None:
        data["short_name"] = manifest.short_name
    if manifest.theme_color is not None:
        data["theme_color"] = manifest.theme_color
    if manifest.background_color is not None:
        data["background_color"] = manifest.background_color
    if manifest.icons:
        data["icons"] = [
            {key: value for key, value in asdict(icon).items() if value is not None} for icon in manifest.icons
        ]
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"
