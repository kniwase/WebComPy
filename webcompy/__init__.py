from . import (
    brython,
    aio,
    ajax,
    app,
    components,
    elements,
    exception,
    reactive,
    router,
    utils,
)

if brython.browser:
    cli = None
else:
    from . import cli


__all__ = [
    "brython",
    "app",
    "reactive",
    "elements",
    "components",
    "router",
    "exception",
    "aio",
    "ajax",
    "utils",
    "cli",
]
