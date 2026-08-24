"""In-page test runner executing browser test functions inside a real PyScript runtime."""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import io
import json
import re
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout, suppress
from dataclasses import dataclass
from types import ModuleType
from typing import Any, cast

from webcompy.app import WebComPyApp, WebComPyAppConfig
from webcompy.components import define_component
from webcompy.di import inject
from webcompy.ports._browser._ffi import BrowserFFIPort
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, FFI_PORT_KEY
from webcompy.utils import ENVIRONMENT

_MANIFEST_URL = "/_webcompy-test/manifest.json"
_PARAM_SUFFIX_RE = re.compile(r"\[p(\d+)\]$")
_DISPLAY_ID_SUFFIX_RE = re.compile(r"\[[^\[\]]*\]$")
_FIXTURE_NAMES = ("app", "dom_root")
_TESTS_MOUNT_ROOT = "/home/pyodide/tests/browser/"
_WC_SRC_MOUNT_ROOT = "/home/pyodide/_wc_src/"
_TB_REWRITES: tuple[tuple[str, str], ...] = (
    (_TESTS_MOUNT_ROOT, "tests/browser/"),
    (f"{_WC_SRC_MOUNT_ROOT}webcompy/", "packages/webcompy/src/webcompy/"),
    (
        f"{_WC_SRC_MOUNT_ROOT}webcompy_testing/",
        "packages/webcompy-testing/src/webcompy_testing/",
    ),
    (
        f"{_WC_SRC_MOUNT_ROOT}webcompy_server/",
        "packages/webcompy-server/src/webcompy_server/",
    ),
)


class UnknownFixtureError(NameError):
    """Raised when a browser test declares a parameter outside the fixture registry."""

    def __init__(self, name: str) -> None:
        super().__init__(f"unknown fixture '{name}'; available fixtures: {', '.join(_FIXTURE_NAMES)}")


class _Skipped(Exception):
    pass


@dataclass
class _ShimMark:
    name: str
    args: tuple[Any, ...]


def _shim_parametrize(argnames: Any, values: list[Any]):
    def decorate(func):
        existing = getattr(func, "pytestmark", [])
        func.pytestmark = [*existing, _ShimMark("parametrize", (argnames, values))]
        return func

    return decorate


def _shim_skip(reason: str = "") -> None:
    raise _Skipped(reason or "skipped")


def _shim_fail(message: str = "") -> None:
    raise AssertionError(message)


def _build_pytest_shim() -> ModuleType:
    mark = ModuleType("pytest.mark")
    mark.parametrize = _shim_parametrize  # type: ignore[attr-defined]
    shim = ModuleType("pytest")
    shim.mark = mark  # type: ignore[attr-defined]
    shim.skip = _shim_skip  # type: ignore[attr-defined]
    shim.fail = _shim_fail  # type: ignore[attr-defined]
    return shim


def _ensure_pytest_shim() -> None:
    if ENVIRONMENT != "pyscript":
        return
    if "pytest" in sys.modules or importlib.util.find_spec("pytest") is not None:
        return
    sys.modules["pytest"] = _build_pytest_shim()


@define_component("browser-test-default-root")
def BrowserTestDefaultRoot(context):
    from webcompy.elements import html

    return html.DIV({})


def _make_default_app() -> WebComPyApp:
    """Create a fresh application instance for tests without a ``get_app`` hook.

    A new ``WebComPyApp`` per test keeps app-owned state (RPC procedure
    registry, deferred operations, plugin manager) from leaking between
    test executions sharing the harness interpreter.
    """
    return WebComPyApp(
        root_component=BrowserTestDefaultRoot,
        config=WebComPyAppConfig(),
    )


class _TrackingFFIPort(BrowserFFIPort):
    def __init__(self) -> None:
        super().__init__()
        self._proxies: list[Any] = []

    def create_proxy(self, obj: Any) -> Any:
        proxy = super().create_proxy(obj)
        self._proxies.append(proxy)
        return proxy

    def destroy_all(self) -> None:
        for proxy in self._proxies:
            with suppress(Exception):
                self.destroy_proxy(proxy)
        self._proxies.clear()


def bootstrap() -> None:
    """Expose ``run_one`` on ``window`` and mark the harness page ready."""
    _ensure_pytest_shim()
    ffi = importlib.import_module("pyscript").ffi
    js = importlib.import_module("js")
    js.window.__webcompy_test__ = ffi.create_proxy({"run_one": run_one})
    js.document.documentElement.setAttribute("data-webcompy-test-ready", "1")


def skip(reason: str = "skipped") -> None:
    """Raise a skip signal that maps to a skipped pytest outcome."""
    raise _Skipped(reason)


def parse_test_id(test_id: str) -> tuple[str, str, int | None]:
    """Split a dispatched test id into module name, qualname, and param index."""
    match = _PARAM_SUFFIX_RE.search(test_id)
    param_index = int(match.group(1)) if match else None
    node_id = test_id[: match.start()] if match else test_id
    module_path, sep, qualname = node_id.partition("::")
    if not sep or not qualname:
        raise ValueError(f"malformed test id: {test_id!r}")
    display_group = _DISPLAY_ID_SUFFIX_RE.search(qualname)
    if display_group is not None:
        qualname = qualname[: display_group.start()]
    module_name = module_path.removesuffix(".py").replace("/", ".")
    return module_name, qualname, param_index


def normalize_traceback(text: str) -> str:
    """Rewrite Emscripten FS source paths back to repo-relative paths."""
    for mounted, repo_relative in _TB_REWRITES:
        text = text.replace(mounted, repo_relative)
    return text


def resolve_parametrize_payload(func: Any, param_index: int | None) -> dict[str, Any]:
    """Resolve ``@pytest.mark.parametrize`` values for the given index."""
    marks = [mark for mark in getattr(func, "pytestmark", []) if getattr(mark, "name", "") == "parametrize"]
    if not marks:
        if param_index is not None:
            raise ValueError(
                f"test id carries parametrize index [{param_index}] but the function has no parametrize mark"
            )
        return {}
    if len(marks) > 1:
        raise ValueError(
            "stacked @pytest.mark.parametrize marks are not supported in the browser test tier; use a single mark"
        )
    raw_names, values = marks[0].args
    if isinstance(raw_names, str):
        names = [name.strip() for name in raw_names.split(",")]
    else:
        names = [str(name) for name in raw_names]
    if param_index is None:
        raise ValueError("parametrized browser test dispatched without a [p<index>] suffix")
    payload = values[param_index]
    if len(names) == 1:
        return {names[0]: payload}
    return dict(zip(names, payload, strict=True))


async def _fetch_manifest_modules() -> list[str]:
    try:
        pyfetch = importlib.import_module("pyodide.http").pyfetch
        response = await pyfetch(_MANIFEST_URL)
        data = await response.json()
        return list(data.get("modules", []))
    except Exception:
        return []


async def _load_function(module_name: str, qualname: str) -> Any:
    sys.modules.pop(module_name, None)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        manifest = await _fetch_manifest_modules()
        if module_name in manifest:
            sys.modules.pop(module_name, None)
            module = importlib.import_module(module_name)
        else:
            raise
    target: Any = module
    for part in qualname.split("::"):
        target = getattr(target, part)
    if not callable(target):
        raise TypeError(f"'{qualname}' resolved to a non-callable object")
    return target


def _sweep_dom_roots() -> None:
    js = importlib.import_module("js")
    children = [child for child in js.document.body.childNodes]
    for child in children:
        if child.nodeName == "DIV" and child.getAttribute("id") != "webcompy-app":
            child.remove()


def _make_dom_root() -> Any:
    js = importlib.import_module("js")
    dom_root = js.document.createElement("div")
    dom_root.setAttribute("data-webcompy-test-root", "")
    js.document.body.appendChild(dom_root)
    return dom_root


def _make_test_context(module: ModuleType) -> tuple[WebComPyApp, Any, _TrackingFFIPort]:
    factory = getattr(module, "get_app", None)
    app: WebComPyApp = cast("WebComPyApp", factory()) if callable(factory) else _make_default_app()
    ctx: Any = app.create_render_context()
    tracking_port = _TrackingFFIPort()
    ctx.di_scope.provide(FFI_PORT_KEY, tracking_port)
    return app, ctx, tracking_port


def _fixture_kwargs(func: Any, app: WebComPyApp, dom_root: Any, exclude: set[str]) -> dict[str, Any]:
    registry: dict[str, Any] = {"app": app, "dom_root": dom_root}
    kwargs: dict[str, Any] = {}
    for name in inspect.signature(func).parameters:
        if name in exclude:
            continue
        if name not in registry:
            raise UnknownFixtureError(name)
        kwargs[name] = registry[name]
    return kwargs


def _console_error_texts(buffer: Any, start: int) -> list[str]:
    entries = buffer.slice(start)
    return [str(entries[index].text) for index in range(entries.length)]


def _dump_result(
    status: str,
    started: float,
    exc_type: str | None,
    tb: str,
    stdout: str,
    stderr: str,
    console_errors: list[str],
) -> str:
    return json.dumps(
        {
            "status": status,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "exc_type": exc_type,
            "traceback": tb,
            "stdout": stdout,
            "stderr": stderr,
            "console_error_delta": console_errors,
        }
    )


async def run_one(test_id: str) -> str:
    """Execute one browser test function and return its result as a JSON string."""
    js = importlib.import_module("js")
    console_buffer = js.window.__webcompy_test_console__
    console_start = console_buffer.length
    started = time.perf_counter()
    stdout_io = io.StringIO()
    stderr_io = io.StringIO()
    module_name = ""
    ctx: Any = None
    tracking_port: _TrackingFFIPort | None = None
    dom_root: Any = None
    try:
        module_name, qualname, param_index = parse_test_id(test_id)
        func = await _load_function(module_name, qualname)
        _sweep_dom_roots()
        _module, ctx, tracking_port = _make_test_context(sys.modules[module_name])
        dom_root = _make_dom_root()
        kwargs = resolve_parametrize_payload(func, param_index)
        kwargs.update(_fixture_kwargs(func, _module, dom_root, exclude=set(kwargs)))
        with redirect_stdout(stdout_io), redirect_stderr(stderr_io):
            outcome = func(**kwargs)
            if inspect.iscoroutine(outcome):
                await outcome
        return _dump_result(
            "passed",
            started,
            None,
            "",
            stdout_io.getvalue(),
            stderr_io.getvalue(),
            _console_error_texts(console_buffer, console_start),
        )
    except _Skipped as e:
        return _dump_result(
            "skipped",
            started,
            type(e).__name__,
            str(e),
            stdout_io.getvalue(),
            stderr_io.getvalue(),
            _console_error_texts(console_buffer, console_start),
        )
    except Exception as e:
        formatted = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        return _dump_result(
            "failed",
            started,
            type(e).__name__,
            normalize_traceback(formatted),
            stdout_io.getvalue(),
            stderr_io.getvalue(),
            _console_error_texts(console_buffer, console_start),
        )
    finally:
        try:
            if ctx is not None:
                try:
                    scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
                    await scheduler.await_pending()
                except Exception:
                    pass
                ctx.dispose()
        finally:
            if dom_root is not None:
                with suppress(Exception):
                    dom_root.remove()
            _sweep_dom_roots()
            if tracking_port is not None:
                tracking_port.destroy_all()
            if module_name:
                sys.modules.pop(module_name, None)
