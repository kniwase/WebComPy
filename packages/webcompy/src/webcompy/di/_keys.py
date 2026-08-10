from __future__ import annotations

from typing import Any

from webcompy.di._key import InjectKey

_ROUTER_KEY = InjectKey[object]("webcompy-internal-router")
RPC_REGISTRY_KEY = InjectKey[object]("webcompy-rpc-registry")
_COMPONENT_STORE_KEY = InjectKey[object]("webcompy-internal-component-store")
_HEAD_PROPS_KEY = InjectKey[object]("webcompy-internal-head-props")
SUSPENSE_RESOLVING_KEY = InjectKey[bool]("webcompy-internal-suspense-resolving")
ERROR_POLICY_KEY = InjectKey[str]("webcompy-error-policy")
HYDRATION_DATA_KEY = InjectKey[dict[str, Any]]("webcompy-hydration-data")
HYDRATION_SIGNAL_DATA_KEY = InjectKey[dict[str, dict[str, Any]]]("webcompy-hydration-signal-data")
RESOURCE_DATA_KEY = InjectKey[dict[str, str]]("webcompy-resource-data")
_STORAGE_SYNC_REGISTRY_KEY = InjectKey[object]("webcompy-internal-storage-sync-registry")
