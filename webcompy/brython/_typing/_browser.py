from typing import Final, Literal


ENVIRONMENT: Final[Literal["browser", "server"]]


try:
    from browser import *  # type: ignore
    from browser import (  # type: ignore
        aio,  # type: ignore
        local_storage,  # type: ignore
        markdown,  # type: ignore
        object_storage,  # type: ignore
        session_storage,  # type: ignore
        svg,  # type: ignore
        timer,  # type: ignore
        websocket,  # type: ignore
        worker,  # type: ignore
    )
    import javascript  # type: ignore

    ENVIRONMENT = "browser"  # type: ignore
except ModuleNotFoundError:
    ENVIRONMENT = "server"  # type: ignore
