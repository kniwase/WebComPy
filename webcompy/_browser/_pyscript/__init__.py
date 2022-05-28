from types import ModuleType
from importlib import import_module


class _PyScriptBrowserModule(ModuleType):
    def __init__(self) -> None:
        super().__init__("_module")
        self.__setattr__(
            "pyodide",
            import_module("pyodide"),
        )
        js = import_module("js")
        for name in dir(js):
            if not name.startswith("_"):
                self.__setattr__(
                    name,
                    getattr(js, name),
                )


browser = _PyScriptBrowserModule()
__all__ = ["browser"]
