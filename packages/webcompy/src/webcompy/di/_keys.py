from __future__ import annotations

from webcompy.di._key import InjectKey

_ROUTER_KEY = InjectKey[object]("webcompy-internal-router")
_COMPONENT_STORE_KEY = InjectKey[object]("webcompy-internal-component-store")
_HEAD_PROPS_KEY = InjectKey[object]("webcompy-internal-head-props")
# Reserved for SuspenseElement: when True, Component._render() skips awaiting _pending_async_template
SUSPENSE_RESOLVING_KEY = InjectKey[bool]("webcompy-internal-suspense-resolving")
