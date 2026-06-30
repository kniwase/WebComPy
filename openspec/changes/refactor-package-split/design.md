## Context

WebComPy currently ships as a single package (`webcompy`) with no subpackages. All code — browser runtime, server-side rendering, CLI tools, testing utilities — lives in one namespace. This bundling forces all users to install server dependencies (starlette, uvicorn, httpx, sse-starlette, aiofiles) even for pure browser usage.

The port abstraction system already cleanly separates browser and server implementations behind ABCs and DI keys, but the current `RenderContext.__init__` imports both `Browser*Port` and `Server*Port` classes based on `ENVIRONMENT` detection, coupling core to both environments.

The wheel builder currently uses a `_BROWSER_ONLY_EXCLUDE` set (`{"webcompy.cli", "webcompy.ports._server", "webcompy.testing"}`) to strip server-side code from browser wheels. With package separation, this exclusion becomes structural rather than convention-driven.

## Goals / Non-Goals

**Goals:**
- Split into 4 packages: `webcompy` (core/browser), `webcompy-server`, `webcompy-cli`, `webcompy-testing`
- Zero external dependencies for `webcompy` core
- `webcompy[full]` extras installs all 4 packages
- `RenderContext` as ABC with `BrowserRenderContext` and `ServerRenderContext` subclasses
- Preserve `python -m webcompy start` CLI entry point via shim
- Backward-compatible import shims for config and testing imports during transition
- Browser wheel naturally contains only `webcompy` core without exclusion lists

**Non-Goals:**
- Changing public API names or subpackage organization within core
- Fixing existing circular dependencies or code quality issues
- Changing the wheel format, lockfile format, or PyScript bootstrap mechanism
- Adding type-check enforcement of cross-package import boundaries (future lint rule)
- Changing `webcompy init` template beyond import path updates

## Decisions

### Decision 1: uv workspace with `packages/` directory

Flat layout under `packages/`:

```
workspace_root/
├── pyproject.toml              # [tool.uv.workspace] members = ["packages/*"]
├── packages/
│   ├── webcompy/               # src/webcompy/
│   ├── webcompy-server/        # src/webcompy_server/
│   ├── webcompy-cli/           # src/webcompy_cli/
│   └── webcompy-testing/       # src/webcompy_testing/
```

**Alternatives considered:**
- Namespace packages (`webcompy.core`, `webcompy.cli`): Rejected because namespace packages require `__init__.py` gymnastics and confuse tooling. Flat names are simpler and conventional.
- Single `packages/` with `src/` layout: Chosen. Each package has its own `src/` for clean separation of source and build artifacts.

### Decision 2: Flat package names (not namespace)

| Package | Install name | Import name |
|---------|-------------|-------------|
| Core | `webcompy` | `webcompy` |
| Server | `webcompy-server` | `webcompy_server` |
| CLI | `webcompy-cli` | `webcompy_cli` |
| Testing | `webcompy-testing` | `webcompy_testing` |

**Rationale:** Each package has its own top-level namespace. This avoids namespace package complexity while keeping the association with WebComPy clear through the naming prefix.

### Decision 3: RenderContext as ABC with constructor injection

```python
# core: webcompy/app/_render_context.py
class RenderContext(ABC):
    def __init__(
        self,
        app,
        path=None,
        *,
        initial_theme: Any = None,       # added in #178 (UI toolkit)
        cookie_header: str | None = None, # added in #178 (UI toolkit)
    ):
        # shared init: DIScope, ComponentStore, Router
        if ENVIRONMENT == "pyscript":
            _set_app_di_scope(self._di_scope)
            _set_app_instance(self)
        self._register_ports()
        # Theme initialization (shared; added in #178)
        from webcompy.ui.theme._manager import ThemeManager
        from webcompy.ui.theme._theme import THEME_KEY, Theme
        theme_value = ...  # resolve from initial_theme, cookie, or config
        self._di_scope.provide(THEME_KEY, ThemeManager(app, self, theme_value))
    
    @abstractmethod
    def _register_ports(self) -> None: ...

class BrowserRenderContext(RenderContext):
    def _register_ports(self) -> None:
        # provision 7 Browser*Port instances (incl. BrowserMediaQueryPort)

# core: webcompy/app/_app.py
class WebComPyApp:
    def __init__(self, ..., _render_context_class=None):
        self._render_context_class = _render_context_class  # default: None → BrowserRenderContext
    
    def create_render_context(self, path=None, *, initial_theme=None, cookie_header=None):
        cls = self._render_context_class or BrowserRenderContext
        ctx = cls(self, path, initial_theme=initial_theme, cookie_header=cookie_header)
        ...
```

```python
# server: webcompy_server/__init__.py
def configure_server_context(app):
    app._render_context_class = ServerRenderContext
```

```python
# server: webcompy_server/_context.py
class ServerRenderContext(RenderContext):
    def _register_ports(self) -> None:
        # provision 7 Server*Port instances (incl. ServerMediaQueryPort)
        # ServerCookiePort uses self._cookie_header from base __init__
        self._di_scope.provide(COOKIE_PORT_KEY, ServerCookiePort(self._cookie_header))
    
    async def render_html(self, **kwargs) -> str:       # async (added in #177)
        return await generate_html(self, **kwargs)
```

**Alternatives considered:**
- Module-level registry (`set_render_context_class(ServerRenderContext)`): Rejected. Global state causes issues with parallel tests and is less explicit.
- DI-based factory (`inject(RENDER_CONTEXT_FACTORY)(app, path)`): Rejected. Circular — `RenderContext` creates the DI scope, so it can't be created by one.
- `WebComPyApp` subclassing: Rejected. Too invasive for user-facing API.

### Decision 4: `render_html()` stays on `RenderContext` as overridable async method

`render_html()` is `async def` (introduced by #177 async rendering pipeline, then reverted to sync in #178 — our implementation targets the sync base with async override). `BrowserRenderContext.render_html()` raises `WebComPyException`. `ServerRenderContext` provides `async def` implementation using `webcompy_server._html.generate_html`.

**Rationale:** `render_html()` is the primary API used by both CLI (`_server.py`, `_generate.py`) and testing (`_asgi.py`). Keeping it on `RenderContext` preserves the existing calling convention. The lazy import of `webcompy.cli._html` in core is removed.

### Decision 5: CLI shim in core `__main__.py`

```python
# webcompy/__main__.py (core)
try:
    from webcompy_cli._argparser import main as _cli_main
    _cli_main()
except ImportError:
    print("webcompy-cli is not installed. Install with: pip install webcompy[cli]", file=sys.stderr)
    sys.exit(1)
```

**Rationale:** `python -m webcompy start` is the documented entry point. Preserving it avoids breaking all existing documentation and muscle memory. `python -m webcompy_cli start` also works as an alternative.

### Decision 6: Backward-compatible import shims for config and testing

**Config shim** (`webcompy/cli/config/__init__.py` keeps re-exporting):

```python
# webcompy/cli/config/__init__.py (shim, kept in core)
try:
    from webcompy_cli.config import WebComPyBuildConfig, WebComPyServerConfig, LockfileSyncConfig
except ImportError:
    WebComPyBuildConfig = None  # type: ignore
    WebComPyServerConfig = None  # type: ignore
    LockfileSyncConfig = None  # type: ignore
```

**Testing shim** (`webcompy/testing/__init__.py` keeps re-exporting):

```python
# webcompy/testing/__init__.py (shim, kept in core)
try:
    from webcompy_testing import (
        TestRenderer, TestRendererResult, FakeDOMNode,
        FakeBrowserDOMPort, FakeBrowserFFIPort, FakeBrowserHostPort,
        FakeFetchPort, create_test_app, render_app_html,
        create_test_asgi_app, format_html, mock_app_run, VirtualDOMEvent,
    )
except ImportError:
    # all symbols set to None
    ...
```

**Rationale:** Existing projects with `from webcompy.cli.config import WebComPyBuildConfig` or `from webcompy.testing import TestRenderer` continue to work. The shim emits a deprecation warning. Can be removed in a future major version.

### Decision 7: Server ports move to `webcompy_server.ports`

```
webcompy_server/
└── ports/
    ├── __init__.py          # re-exports all Server*Port classes + VirtualDOMNode/Event
    ├── _dom.py              # ServerDOMPort
    ├── _fetch.py            # ServerFetchPort
    ├── _ffi.py              # ServerFFIPort
    ├── _host.py             # ServerHostPort
    ├── _cookie.py           # ServerCookiePort (accepts cookie_header)
    ├── _history.py          # ServerHistoryPort
    ├── _media_query.py      # ServerMediaQueryPort (added in #178)
    └── _virtual_dom.py      # VirtualDOMNode, VirtualDOMEvent
```

**Rationale:** Flat mirror of the core `webcompy/ports/` structure. The `_server` suffix is no longer needed since the package name already distinguishes it.

### Decision 8: Dependency injection keys stay in core

All 7 `InjectKey` constants (`DOM_PORT_KEY`, `FFI_PORT_KEY`, `FETCH_PORT_KEY`, `COOKIE_PORT_KEY`, `HISTORY_PORT_KEY`, `HOST_PORT_KEY`, `MEDIA_QUERY_PORT_KEY`) stay in `webcompy/ports/_keys.py`. Server and testing packages import them from core.

**Rationale:** Keys are the contract between port consumers (components, elements, router, ajax) and port providers (browser/server implementations). Consumers need keys without importing servers. Keys must live where consumers live (= core).

### Decision 9: Extras on `webcompy` package

```toml
# packages/webcompy/pyproject.toml
[project.optional-dependencies]
server  = ["webcompy-server"]
cli     = ["webcompy-cli"]
testing = ["webcompy-testing"]
full    = ["webcompy-server", "webcompy-cli", "webcompy-testing"]
```

**Rationale:** `pip install webcompy[full]` is the one-stop install. `pip install webcompy` alone gives minimal browser core. This is the standard Python extras pattern, no need for a separate meta-package.

### Decision 10: Theme system (`webcompy/ui/`) stays in core

The theme system (`webcompy/ui/theme/`, `webcompy/ui/code_block/`, `webcompy/ui/_composables/`, `webcompy/ui/_styles/`) added in #178 is browser-facing code used by components at runtime. It stays in the `webcompy` core package. CSS files in `webcompy/ui/_styles/` are bundled into the framework wheel (the wheel builder's `_collect_package_files` already handles non-Python files since #178). Theme initialization logic (`ThemeManager`) is part of the shared `RenderContext.__init__` base class.

**Rationale:** The UI toolkit is part of the component runtime, not server tooling. It belongs in the browser core.

### Decision 11: Documentation files updated for multi-package structure

`README.md`, `README.ja.md`, `CONTRIBUTING.md`, and `AGENTS.md` SHALL be updated to reflect the new package structure:

- **README.md/README.ja.md**: Installation instructions show `pip install webcompy[full]` for full stack, `pip install webcompy[cli]` for CLI-only, etc. Feature descriptions clarify which package provides which capability (core vs extra).
- **CONTRIBUTING.md**: Development setup references uv workspace. Quick commands reflect the new workspace structure (e.g., ruff/pyright run from workspace root, pytest runs across workspace).
- **AGENTS.md**: Project Structure section shows `packages/` layout with 4 sub-packages. File→Spec Mapping table gains rows for `webcompy_server/ports/`, `webcompy_cli/`, `webcompy_testing/`. The dual-environment description narrows "single codebase" guarantee to core only.

**Rationale:** The developer experience changes meaningfully with the split (different install paths, new workspace layout). Documentation must keep pace.

## Files to Move

| Source (current) | Destination (after) |
|---|---|
| `webcompy/ports/_server/` (all files) | `packages/webcompy-server/src/webcompy_server/ports/` |
| `webcompy/cli/_html.py` | `packages/webcompy-server/src/webcompy_server/_html.py` |
| `webcompy/cli/` (remaining files) | `packages/webcompy-cli/src/webcompy_cli/` |
| `webcompy/testing/` (all files) | `packages/webcompy-testing/src/webcompy_testing/` |

## Risks / Trade-offs

- **[Risk] User-facing import path breakage for config and testing**: Existing projects with `from webcompy.cli.config import WebComPyBuildConfig` will break if they update without the new package. → **Mitigation**: Shim modules kept in core that re-export with deprecation warning. Full removal deferred to major version bump.
- **[Risk] `webcompy init` template breakage**: Generated `webcompy_config.py` uses old import paths. → **Mitigation**: Template updated to use new paths. Existing projects get shim support during transition.
- **[Risk] `python -m webcompy start` without `webcompy-cli` installed**: Users who `pip install webcompy` (core only) get a clean error message, but it's a behavior change from today where it works. → **Mitigation**: Clear error message pointing to `pip install webcompy[cli]`. `webcompy[full]` recommended in docs.
- **[Risk] Double-publish complexity**: Two packages (`webcompy` core + browser wheel) to PyPI. Browser wheel published separately from PyPI core. → **Mitigation**: CI matrix handles both. Document publish workflow.
- **[Risk] Import shims may cause circular import issues**: If shim modules inadvertently import from moved packages during module initialization. → **Mitigation**: All shims use lazy `try/except ImportError` inside function scope, not at module level where possible.

## Open Questions

- Should `PluginScript` stay in `webcompy/app/_config.py` (core) or move? → Currently used by both `plugin/_plugin.py` (core) and `cli/_html.py` (moves to server). Both need it. Keep in core.
- Should `webcompy/ports/_browser/_raw.pyi` stub file move? → No, stays in core. Browser type stubs are part of the browser API.
