import warnings

warnings.warn(
    "Importing from webcompy.cli.config is deprecated. Use 'from webcompy_cli.config import ...' instead.",
    DeprecationWarning,
    stacklevel=2,
)

try:
    from webcompy_cli.config import (  # type: ignore[unused-import]
        LockfileSyncConfig,
        WebComPyBuildConfig,
        WebComPyServerConfig,
    )
except ImportError:
    LockfileSyncConfig = None
    WebComPyBuildConfig = None
    WebComPyServerConfig = None
