from __future__ import annotations

import importlib

from webcompy.components._generator import ComponentGenerator
from webcompy.components._libs import generate_id
from webcompy.router._pages import WebComPyRouterException


class LazyComponentGenerator(ComponentGenerator):
    _import_path: str
    _caller_file: str
    _resolved: ComponentGenerator | None
    _resolve_error: bool

    def __init__(self, import_path: str, caller_file: str) -> None:
        self._import_path = import_path
        self._caller_file = caller_file
        self._resolved = None
        self._resolve_error = False
        attr_name = import_path.rsplit(":", 1)[-1]
        self._name = attr_name
        self._id = generate_id(attr_name)
        self._style = {}
        self._component_def = None
        self._registered = False

    def _resolve(self) -> ComponentGenerator:
        if self._resolved is None:
            module_path, attr_name = self._import_path.rsplit(":", 1)
            module = importlib.import_module(module_path)
            resolved = getattr(module, attr_name)
            if not isinstance(resolved, ComponentGenerator):
                raise WebComPyRouterException(f"'{self._import_path}' is not a ComponentGenerator")
            self._resolved = resolved
            self._component_def = resolved._component_def
            self._name = resolved._name
            self._id = resolved._id
            self._style = resolved._style
            self._registered = resolved._registered
            resolved._try_register()
        return self._resolved

    def _preload(self) -> None:
        try:
            self._resolve()
        except Exception:
            self._resolve_error = True

    def __call__(self, props, *, slots=None):
        resolved = self._resolve()
        return resolved(props, slots=slots)

    def __getattr__(self, name: str):
        return getattr(self._resolve(), name)

    @property
    def scoped_style(self):
        return self._resolve().scoped_style

    @scoped_style.setter
    def scoped_style(self, value):
        self._resolve().scoped_style = value


def lazy(import_path: str, caller_file: str) -> ComponentGenerator:
    if ":" not in import_path:
        raise WebComPyRouterException(f"lazy() import_path must be 'module:Attribute' format, got: {import_path!r}")
    module_path, attr_name = import_path.rsplit(":", 1)
    if not module_path or not attr_name:
        raise WebComPyRouterException(
            f"lazy() import_path must have non-empty module and attribute, got: {import_path!r}"
        )
    if module_path.startswith("."):
        raise WebComPyRouterException(
            f"lazy() import_path does not support relative module paths, got: {import_path!r}"
        )
    if not caller_file:
        raise WebComPyRouterException("lazy() caller_file must not be empty")
    return LazyComponentGenerator(import_path, caller_file)
