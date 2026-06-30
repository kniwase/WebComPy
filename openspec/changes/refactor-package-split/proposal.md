## Why

WebComPy currently ships as a single monolithic package, bundling browser runtime, server-side rendering, CLI tools, and testing utilities together. This forces all users to install heavy server dependencies (starlette, uvicorn, httpx, sse-starlette, aiofiles) even when they only need the browser-side framework. It also prevents publishing the browser core to PyPI as a standalone package for PyScript's `py-config.packages` consumption.

Splitting into 4 packages under a uv workspace enables each component to carry only its own dependencies, reduces browser wheel size, and makes the architecture boundaries explicit.

## What Changes

- **New packages**: `webcompy-server`, `webcompy-cli`, `webcompy-testing` created alongside existing `webcompy` (core)
- **Core (`webcompy`)** becomes zero-dependency (pure Python). Holds exception, utils, di, signal, ports (ABC + browser impls), aio, ajax, elements, components, router, plugin, app (including `BrowserRenderContext`), and the ABC `RenderContext`
- **`webcompy-server`** holds `ports/_server/` (ServerDOMPort, ServerFetchPort, VirtualDOMNode, etc.), `_html.py` (HTML template generation), and `ServerRenderContext(RenderContext)`. Dependencies: `webcompy`, `httpx`
- **`webcompy-cli`** holds `start`, `generate`, `init`, `lock`, `inspect`, wheel builder, config classes, and template data. Dependencies: `webcompy`, `webcompy-server`, `starlette`, `uvicorn`, `sse-starlette`, `aiofiles`, `packaging` (soft), `playwright` (optional)
- **`webcompy-testing`** holds `TestRenderer`, `FakeBrowser*Port`, `create_test_app`, `render_app_html`, `create_test_asgi_app`. Dependencies: `webcompy`, `webcompy-server`, `starlette`, `beautifulsoup4`
- **`RenderContext` ABC-ified**: core defines `RenderContext(ABC)` and `BrowserRenderContext`. `webcompy-server` provides `ServerRenderContext`. `WebComPyApp` accepts an injectable `_render_context_class` (default: `BrowserRenderContext`)
- **Extras on `webcompy` package**: `pip install webcompy[full]` installs all 4 packages. `pip install webcompy[server]`, `webcompy[cli]`, `webcompy[testing]` install subsets
- **`python -m webcompy start` preserved** via core `__main__.py` shim that delegates to `webcompy_cli` when available
- **Config import path**: `webcompy_config.py` changes `from webcompy.cli.config` to `from webcompy_cli.config`. Legacy import path shim provided during transition
- **Wheel builder** simplified: no more `_BROWSER_ONLY_EXCLUDE` — browser wheel naturally contains only `webcompy` (core)
- **`packages/*`** directory layout under uv workspace root
- **README / CONTRIBUTING / AGENTS.md** updated: installation instructions reflect extras pattern, project structure shows workspace layout, file→spec mapping includes new package paths

## Capabilities

### New Capabilities

- `package-topology`: Defines the 4-package architecture, their contents, public APIs, and inter-package dependency graph
- `render-context-abc`: Defines `RenderContext` as ABC with `_register_ports()` abstract method, and the injection mechanism for `BrowserRenderContext`/`ServerRenderContext`
- `port-provisioning`: Defines how server/browser port implementations are registered without cross-package imports
- `meta-package-extras`: Defines the `webcompy[full/server/cli/testing]` extras for installing package subsets

### Modified Capabilities

- `architecture`: Package structure changes from single `webcompy/` to multi-package under `packages/`. Port provisioning boundary moves from monolithic to layered.
- `cli`: Import paths change to `webcompy_cli.*`. Config file import path changes. Wheel builder no longer needs `_BROWSER_ONLY_EXCLUDE`.
- `testing-module`: Package moves to `webcompy_testing`. Imports change accordingly.
- `virtual-dom`: Moves to `webcompy_server` package.
- `wheel-builder`: Browser wheel contains only `webcompy` (core), not `webcompy-cli`/`webcompy-server`/`webcompy-testing`. `_BROWSER_ONLY_EXCLUDE` removed.
- `app-config`: `WebComPyAppConfig` stays in core. `WebComPyBuildConfig`/`WebComPyServerConfig` move to `webcompy_cli` with legacy shim.
- `config-separation`: Structurally enforced by separate packages rather than by convention.
- `project-config`: Config template and `webcompy init` scaffold updated for new import paths. Migration shim for existing projects.
- `render-context`: ABC-ified with `_register_ports()` abstract method. Port provisioning extracted from core init.

## Impact

- **Affected code**: `webcompy/app/_render_context.py` (ABC-ified), `webcompy/app/_app.py` (injectable `_render_context_class`), `webcompy/cli/` (moves to new `webcompy_cli`), `webcompy/ports/_server/` (moves to `webcompy_server`), `webcompy/testing/` (moves to `webcompy_testing`), `webcompy/__init__.py`, `webcompy/__main__.py` (shim), `pyproject.toml` (workspace root), template data
- **Affected docs**: `README.md`, `README.ja.md` (installation instructions, feature descriptions), `CONTRIBUTING.md` (workspace setup, dev commands), `AGENTS.md` (project structure, file→spec mapping, CI pipeline reference)
- **Breaking changes**:
  - `python -m webcompy start` requires `webcompy-cli` installed (core alone won't work)
  - `from webcompy.cli.config import WebComPyBuildConfig` → `from webcompy_cli.config import WebComPyBuildConfig` (legacy shim provided)
  - `from webcompy.testing import TestRenderer` → `from webcompy_testing import TestRenderer`
  - `from webcompy.ports._server._virtual_dom import VirtualDOMNode` → `from webcompy_server.ports import VirtualDOMNode`
- **Non-breaking**: All user-facing component/rendering APIs (`webcompy.elements`, `webcompy.components`, `webcompy.signal`, `webcompy.router`) remain at same import paths

## Known Issues Addressed

N/A — this is a structural refactoring, not addressing any known functional issues.

## Non-goals

- Fixing circular dependencies (`elements` ↔ `components`, `app` ↔ `cli`)
- Porting remaining `from pyscript import context` (4 locations) to port abstraction
- Porting `ajax/_fetch.py` form submission bypass of `FetchPort`
- Removing `_app_di_scope` module-level global from `di/_scope.py`
- Renaming any subpackages or public APIs within `webcompy` core
