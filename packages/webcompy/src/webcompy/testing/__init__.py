import warnings

warnings.warn(
    "Importing from webcompy.testing is deprecated. Use 'from webcompy_testing import ...' instead.",
    DeprecationWarning,
    stacklevel=2,
)

try:
    from webcompy_testing import (  # type: ignore[unused-import]
        FakeBrowserDOMPort,
        FakeBrowserFFIPort,
        FakeBrowserHostPort,
        FakeDOMNode,
        FakeFetchPort,
        TestRenderer,
        TestRendererResult,
        VirtualDOMEvent,
        create_test_app,
        create_test_asgi_app,
        format_html,
        mock_app_run,
        render_app_html,
        run_sync,
    )
except ImportError:
    FakeBrowserDOMPort = None
    FakeBrowserFFIPort = None
    FakeBrowserHostPort = None
    FakeDOMNode = None
    FakeFetchPort = None
    TestRenderer = None
    TestRendererResult = None
    VirtualDOMEvent = None
    create_test_app = None
    create_test_asgi_app = None
    format_html = None
    mock_app_run = None
    render_app_html = None
    run_sync = None
