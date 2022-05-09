from typing import Final, Literal


def _get_environment() -> Literal["pyscript", "brython", "other"]:
    import platform
    import sys

    if "Emscripten" == platform.system():
        return "pyscript"
    elif "Brython" in sys.version:
        return "brython"
    else:
        return "other"


ENVIRONMENT: Final = _get_environment()
