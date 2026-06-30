from __future__ import annotations

from webcompy.di._key import InjectKey
from webcompy.router._router import Router

RouterKey = InjectKey[Router]("webcompy-router")
