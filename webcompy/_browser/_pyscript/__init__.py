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
            if name.startswith("_"):
                continue
            try:
                attr = getattr(js, name)
            except AttributeError:
                try:
                    attr = import_module("js", name)
                except ModuleNotFoundError:
                    continue
            self.__setattr__(name, attr)


browser = _PyScriptBrowserModule()
__all__ = ["browser"]
