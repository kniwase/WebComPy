from __future__ import annotations

from typing import Any

from webcompy.di._key import InjectKey

_ROUTER_KEY = InjectKey[object]("webcompy-internal-router")
_COMPONENT_STORE_KEY = InjectKey[object]("webcompy-internal-component-store")
_HEAD_PROPS_KEY = InjectKey[object]("webcompy-internal-head-props")
SUSPENSE_RESOLVING_KEY = InjectKey[bool]("webcompy-internal-suspense-resolving")
HYDRATION_DATA_KEY = InjectKey[dict[str, Any]]("webcompy-hydration-data")
HYDRATION_SIGNAL_DATA_KEY = InjectKey[dict[str, dict[str, Any]]]("webcompy-hydration-signal-data")
