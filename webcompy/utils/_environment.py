from typing import Final, Literal


def _get_environment() -> Literal["pyscript", "other"]:
    import platform

    if "Emscripten" == platform.system():
        return "pyscript"
    else:
        return "other"


ENVIRONMENT: Final = _get_environment()
