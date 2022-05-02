from typing import Final, Literal


ENVIRONMENT: Final[Literal["browser", "server"]]


try:
    from browser import *  # type: ignore
    import javascript  # type: ignore

    ENVIRONMENT = "browser"  # type: ignore
except ModuleNotFoundError:
    ENVIRONMENT = "server"  # type: ignore
