"""Predefined ``InjectKey`` constants for framework and app-level DI values."""

from __future__ import annotations

from typing import Any

from webcompy.di._key import InjectKey

_ROUTER_KEY = InjectKey[object]("webcompy-internal-router")
RPC_REGISTRY_KEY = InjectKey[object]("webcompy-rpc-registry")
RPC_MIDDLEWARE_KEY = InjectKey[object]("webcompy-rpc-middleware")
"""Key for the per-context ``RpcMiddlewareRegistry`` consulted by HTTP RPC operations."""
_APP_KEY = InjectKey[object]("webcompy-internal-app")
_COMPONENT_STORE_KEY = InjectKey[object]("webcompy-internal-component-store")
_HEAD_PROPS_KEY = InjectKey[object]("webcompy-internal-head-props")
SUSPENSE_RESOLVING_KEY = InjectKey[bool]("webcompy-internal-suspense-resolving")
"""Key for the flag set while a ``Suspense`` boundary is resolving its async children."""
ERROR_POLICY_KEY = InjectKey[str]("webcompy-error-policy")
HYDRATION_DATA_KEY = InjectKey[dict[str, Any]]("webcompy-hydration-data")
"""Key for the pending async-result payload transferred from SSR to the hydrated client."""
HYDRATION_SIGNAL_DATA_KEY = InjectKey[dict[str, dict[str, Any]]]("webcompy-hydration-signal-data")
"""Key for the signal value payload transferred from SSR to the hydrated client."""
RESOURCE_DATA_KEY = InjectKey[dict[str, str]]("webcompy-resource-data")
"""Key for the cached app-package resource payload transferred from SSR to the hydrated client."""
_STORAGE_SYNC_REGISTRY_KEY = InjectKey[object]("webcompy-internal-storage-sync-registry")
_REALTIME_CONNECTION_REGISTRY_KEY = InjectKey[object]("webcompy-internal-realtime-connection-registry")
_REALTIME_TYPE_REGISTRY_KEY = InjectKey[object]("webcompy-internal-realtime-type-registry")
_TELEPORT_REGISTRY_KEY = InjectKey[object]("webcompy-internal-teleport-registry")
