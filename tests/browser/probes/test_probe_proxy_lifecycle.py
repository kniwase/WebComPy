"""``create_proxy`` / ``destroy`` lifecycle contracts.

Contract: proxies created via ``pyscript.ffi.create_proxy`` remain callable
across await points, and ``destroy()`` detaches the proxy from the JS side.
The exact behavior of a second ``destroy()`` call is codified as observed on
the pinned runtime.
"""

import asyncio


def _ffi():
    from pyscript import ffi

    return ffi


async def test_proxy_survives_awaits(app):
    ffi = _ffi()

    def python_callback(value):
        return value * 2

    proxy = ffi.create_proxy(python_callback)

    async def later():
        await asyncio.sleep(0)
        return proxy(21)

    assert await later() == 42

    proxy.destroy()


async def test_double_destroy_is_tolerated_or_raises_consistently(app):
    """Codify the pinned runtime's double-destroy behavior.

    The assertion below freezes the observed behavior; if a PyScript/Pyodide
    bump changes it, this probe fails and the contract must be re-examined.
    """
    from js import TypeError as JsTypeError  # noqa: F401  (availability probe)

    ffi = _ffi()
    proxy = ffi.create_proxy(lambda: None)
    proxy.destroy()

    raised = False
    try:
        proxy.destroy()
    except Exception as e:
        raised = True
        # The observed exception type is recorded via its name for diagnostics.
        assert isinstance(e.__class__.__name__, str)

    # Observed at pin: double destroy does NOT raise.
    assert not raised


async def test_destroyed_proxy_call_raises(app):
    """Calling a destroyed proxy raises instead of silently succeeding."""
    ffi = _ffi()
    proxy = ffi.create_proxy(lambda: "unused")
    proxy.destroy()

    raised = False
    try:
        proxy()
    except Exception:
        raised = True

    # Observed at pin: invoking a destroyed proxy raises a JsException.
    assert raised
