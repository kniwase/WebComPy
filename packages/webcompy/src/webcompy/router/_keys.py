"""Dependency injection keys for the router."""

from __future__ import annotations

from webcompy.di._key import InjectKey
from webcompy.router._router import Router

RouterKey = InjectKey[Router]("webcompy-router")
"""DI key under which the application ``Router`` is provided."""
