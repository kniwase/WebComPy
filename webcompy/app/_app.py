from __future__ import annotations

import warnings
from typing import Any

from webcompy.app._config import AppConfig
from webcompy.app._root_component import AppDocumentRoot
from webcompy.components import ComponentGenerator
from webcompy.components._component import _set_app_instance
from webcompy.components._generator import ComponentStore
from webcompy.di._keys import _COMPONENT_STORE_KEY
from webcompy.di._scope import DIScope, _set_app_di_scope
from webcompy.exception import WebComPyException
from webcompy.router import Router
from webcompy.utils import ENVIRONMENT


class WebComPyApp:
    _root: AppDocumentRoot
    _di_scope: DIScope
    _config: AppConfig
    _component_store: ComponentStore

    def __init__(
        self,
        *,
        root_component: ComponentGenerator[None],
        router: Router | None = None,
        config: AppConfig | None = None,
    ) -> None:
        self._config = config or AppConfig()
        self._di_scope = DIScope()
        self._component_store = ComponentStore()
        self._di_scope.provide(_COMPONENT_STORE_KEY, self._component_store)
        self._defer_depth: int = 0
        self._deferred_callbacks: list = []
        if ENVIRONMENT == "pyscript":
            self._di_scope.__enter__()
            _set_app_di_scope(self._di_scope)
            _set_app_instance(self)
            from webcompy.components._generator import _register_deferred_components

            _register_deferred_components()
        else:
            with self._di_scope:
                from webcompy.components._generator import _register_deferred_components

                _register_deferred_components()
        self._root = AppDocumentRoot(root_component, router, self._di_scope, app=self)

    @property
    def config(self) -> AppConfig:
        return self._config

    @property
    def di_scope(self) -> DIScope:
        return self._di_scope

    def provide(self, key: object, value: Any) -> None:
        self._di_scope.provide(key, value)

    @property
    def __component__(self):
        warnings.warn(
            "app.__component__ is deprecated. Use app properties directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._root

    @property
    def routes(self):
        return self._root.routes

    @property
    def router_mode(self):
        return self._root.router_mode

    def set_path(self, path: str):
        return self._root.set_path(path)

    @property
    def head(self):
        return self._root.head

    @property
    def style(self):
        return self._root.style

    @property
    def scripts(self):
        return self._root.scripts

    @property
    def set_title(self):
        return self._root.set_title

    @property
    def set_meta(self):
        return self._root.set_meta

    @property
    def append_link(self):
        return self._root.append_link

    @property
    def append_script(self):
        return self._root.append_script

    @property
    def set_head(self):
        return self._root.set_head

    @property
    def update_head(self):
        return self._root.update_head

    def run(self, selector: str = "#webcompy-app") -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("app.run() can only be called in a browser environment.")
        self._root._selector = selector
        self._root.render()
