---
title: CLI Reference
description: Complete command and flag reference for python -m webcompy, exit behavior, lockfile workflows, and browser inspection via webcompy inspect.
---

# CLI Reference

WebComPy exposes its development server, static site generator, scaffolding, dependency lockfile manager, and Playwright browser inspector through `python -m webcompy <subcommand>`. Inside a `uv`-managed project, prefix commands with `uv run` (`uv run python -m webcompy ...`).

## Subcommands at a glance

| Command | Purpose | Key options |
|---|---|---|
| `python -m webcompy start` | Run the dev or production ASGI server | `--dev`, `--port`, `--config`, serving overrides |
| `python -m webcompy generate` | Pre-render routes and assets into a static output directory | `--dist`, `--config`, serving overrides |
| `python -m webcompy init` | Scaffold a starter app package in the current directory | Interactive prompt if files exist |
| `python -m webcompy lock` | Resolve, export, verify, or install browser dependencies | `--config`, `--export`, `--sync`, `--install` |
| `python -m webcompy inspect` | Launch servers and inspect or evaluate pages in Chromium | `serve`, `stop`, `screenshot`, `console`, `query`, `click`, `navigate`, `verify`, `pyexec` |

Running `python -m webcompy` with no subcommand prints top-level help and exits. Passing `--help` on `python -m webcompy`, any subcommand, or any `inspect` sub-subcommand prints usage for that parser.

## Server and build commands

### `start`

Starts the uvicorn ASGI server for your application (`run_server`). By default it serves in production mode on the port configured in `WebComPyServerConfig` (default `8080`); passing `--dev` switches the server to hot-reload mode with `/_webcompy_reload` Server-Sent Events enabled and `uvicorn(..., reload=True)`.

| Flag | Values / type | Description |
|---|---|---|
| `--dev` | flag | Enable development mode with hot reload |
| `--port` | `int` | Override `WebComPyServerConfig.port` |
| `--config` | `str` | Dotted import path to config module (for example `my_project.webcompy_config`) |
| `--serve-all-deps` | flag | Bundle all pure-Python dependencies into the app wheel (default) |
| `--no-serve-all-deps` | flag | Load CDN-available pure-Python dependencies from Pyodide CDN |
| `--wasm-serving` | `cdn` or `local` | Override where WASM wheels load from |
| `--runtime-serving` | `cdn` or `local` | Override where PyScript and Pyodide runtime files load from |
| `--standalone` | flag | Enable standalone local asset serving (`serve_all_deps=True` plus local defaults) |
| `--no-standalone` | flag | Disable standalone mode (CDN defaults) |
| `--wheel-mode` | `bundled` or `split` | Package core framework together with app or as a separate wheel |

`--serve-all-deps` / `--no-serve-all-deps` are mutually exclusive, as are `--standalone` / `--no-standalone`. CLI flags override values read from `webcompy_config.py`.

### `generate`

Runs static site generation (`generate_static_site`) through an in-process `httpx.ASGITransport` client, writing pre-rendered HTML, framework stylesheets, package wheels, allowed resources, copied `static/` files, local runtime/WASM assets (when configured), and optional PWA files into the output directory (`dist` by default).

| Flag | Values / type | Description |
|---|---|---|
| `--dist` | `str` | Override `WebComPyBuildConfig.dist` output directory path |
| `--config` | `str` | Dotted import path to config module |
| `--serve-all-deps` | flag | Bundle all pure-Python dependencies into the app wheel (default) |
| `--no-serve-all-deps` | flag | Load CDN-available pure-Python dependencies from Pyodide CDN |
| `--wasm-serving` | `cdn` or `local` | Override where WASM wheels load from |
| `--runtime-serving` | `cdn` or `local` | Override where PyScript and Pyodide runtime files load from |
| `--standalone` | flag | Enable standalone local asset serving |
| `--no-standalone` | flag | Disable standalone mode |
| `--wheel-mode` | `bundled` or `split` | Package core framework together with app or as a separate wheel |

### `init`

Scaffolds a starter application (`app/`, `webcompy_config.py`, `static/`, and `__init__.py`) in the current working directory. `init` accepts no command-specific flags beyond `--help`. If any target file already exists, it prints the existing paths and prompts interactively to confirm overwriting (`y/N`, defaulting to abort cleanly).

### `lock`

Resolves and validates `webcompy-lock.json` (`lock_command`) next to your app package directory, or runs lockfile export/verification workflows against `requirements.txt` and `pyproject.toml`.

| Flag | Values / type | Description |
|---|---|---|
| `--config` | `str` | Dotted import path to config module |
| `--export` | flag | Export locked pure-Python and WASM package pins to `requirements.txt` and record `requirements_path` if unset |
| `--sync` | flag | Compare `webcompy-lock.json` against `requirements.txt` and `pyproject.toml` |
| `--install` | flag | Export `requirements.txt` and install pinned packages via `uv pip install` or `python -m pip install` |

`--export`, `--sync`, and `--install` are mutually exclusive and require an existing `webcompy-lock.json` (run `python -m webcompy lock` first if missing).

## Inspect subcommands

`python -m webcompy inspect <subcommand>` drives Playwright Chromium headlessly and emits structured JSON on stdout (so scripts and AI tools can parse results cleanly). Installing Playwright is required (`pip install playwright` followed by `playwright install chromium`).

### Server lifecycle: `serve` and `stop`

`inspect serve` launches a detached server process, waits up to 10 seconds for HTTP readiness, records PID metadata under `.tmp/webcompy-inspect/<port>.pid`, and prints `{"port": ..., "url": ..., "pid": ..., "source": "app" | "ssg"}`.

| Subcommand | Positional args | Options | Description |
|---|---|---|---|
| `serve` | — | `--source` (`app` or `ssg`), `--dist`, `--config`, `--dev`, `--port`, `--runtime-serving` | Start an app server or static file server for `dist/` |
| `stop` | `port` (`int`) | `--timeout` (`int`, default `10`) | Send SIGTERM (then SIGKILL after timeout) and remove `.pid`/`.log` files |

Constraints enforced by `inspect serve`:

- `--source=ssg` requires `--dist <dir>` and disallows `--dev` and `--runtime-serving`.
- `--source=app` disallows `--dist`.
- `--port 0` automatically binds an ephemeral free TCP port.

### DOM, console, and interaction checks

All browser-backed `inspect` actions support `--wait-for <selector>` (30s timeout) to wait until PyScript hydrates or an async route renders before executing the check.

| Subcommand | Positional args | Options | Output / contract |
|---|---|---|---|
| `screenshot` | `url` | `--selector`, `--full-page`, `--output`, `--wait-for` | Writes PNG to `--output` (`{"output", "size"}`) or returns base64 JSON (`{"screenshot"}`) |
| `console` | `url` | `--level` (`error`, `warning`, `info`, `log`, `debug`; default `warning`), `--wait` (ms, default `5000`), `--wait-for` | Captures console entries at or above severity into `{"messages": [...]}` |
| `query` | `url`, `selector` | `--property` (`text`, `html`, `attr:NAME`, `visible`, `count`; default `text`), `--wait-for` | Returns `{"results": [...]}` |
| `click` | `url`, `selector` | `--wait-for` | Clicks element, waits up to 10s for `--wait-for`, prints `{"clicked": true, "selector": ...}` |
| `navigate` | `url`, `path` | `--wait-for` | Navigates to normalized URL + path and prints `{"current_url", "title"}` |
| `verify` | `url` | `--expect` (repeatable), `--wait-for` | Evaluates assertions (waits 5s if `--wait-for` omitted), prints `{"passed", "failed"}` |

Supported `--expect` expressions for `inspect verify`:

- `selector=exact text` and `selector*=substring`
- `selector:visible` and `selector:attr:name=value` (use `:attr:` when attribute selectors contain `=`)
- `console:no-error` and `console:no-level=LEVEL`

### In-browser Python evaluation: `pyexec`

`python -m webcompy inspect pyexec` launches a self-contained browser test harness session (serving `/testharness`), waits for the PyScript interpreter sentinel (`html[data-webcompy-test-ready='1']`, 120s startup timeout), and evaluates Python code inside the real PyScript runtime, printing JSON with `stdout`, `stderr`, `result_repr`, `console_error_delta`, `exc_type`, and `traceback`.

| Positional / flag | Type | Description |
|---|---|---|
| `code` | optional `str` | Inline Python snippet for single-shot evaluation |
| `--file` | `str` | Path to a Python file to evaluate |
| `--repl` | flag | Persistent stdin loop evaluating one line per turn until EOF |
| `--repl-timeout` | `int` (default `300`) | Idle timeout in seconds between REPL lines |
| `--wait-for` | `str` | Optional CSS selector to await before evaluating |

`pyexec` always runs inside its isolated harness session and never attaches to a running `webcompy start` server process.

## Exit codes and automation contracts

| Exit code | Meaning |
|---|---|
| `0` | Command completed cleanly, `inspect verify` passed all assertions, or `inspect pyexec --repl` reached EOF |
| `1` | Missing `webcompy-cli` or `playwright`, invalid config/lockfile, server startup or stop error, missing target selector, unknown `--property`, or at least one failed assertion in `inspect verify` |
| `2` | Invalid argparse invocation or invalid `inspect pyexec` flag combination (`--repl` with `code`/`--file`, both `code` and `--file`, nonexistent `--file`, or missing all three) |
| `124` | `inspect pyexec --repl` idle timeout exceeded (`--repl-timeout`) |
| `130` | `inspect pyexec --repl` interrupted by `SIGINT` |

When any unexpected exception occurs during `build` or `generate`, `generate_static_site` propagates it cleanly rather than shipping partial output when static pages fail pre-rendering.

## Worked examples

### Local development server on a custom port

```bash
uv run python -m webcompy start --dev --port 8000 --config my_app.webcompy_config
```

### Static production build with local runtime assets

```bash
uv run python -m webcompy generate --config my_app.webcompy_config --standalone --dist ./public
```

### Lock, audit against pyproject.toml, and export pinned requirements

```bash
uv run python -m webcompy lock --config my_app.webcompy_config
uv run python -m webcompy lock --sync --config my_app.webcompy_config
uv run python -m webcompy lock --export --config my_app.webcompy_config
```

### Headless browser inspection workflow with `inspect`

Start an ephemeral app server, wait for hydration, verify assertions and console cleanliness, run a quick PyScript check, and stop the server cleanly:

```bash
uv run python -m webcompy inspect serve --source app --config my_app.webcompy_config --port 0
uv run python -m webcompy inspect verify http://localhost:PORT/ --wait-for "#webcompy-app" --expect "h1=Dashboard" --expect "console:no-error"
uv run python -m webcompy inspect pyexec "from webcompy.signal import Signal; s = Signal(2); s.value += 3; s.value"
uv run python -m webcompy inspect stop PORT
```

## Next steps

- Configure the fields those flags override in [Project Configuration](/documents/server/project-configuration).
- Understand how `start --dev`, `start`, and `generate` share the SSR pipeline in [SSR & SSG](/documents/advanced/ssr-and-ssg).
- Compare CDN, standalone, and wheel-packaging options in [Serving Modes](/documents/server/serving-modes).
- Run fast browserless component and ASGI tests before reaching for Chromium in [Testing](/documents/server/testing).
- Full API: [Server, CLI, RPC & Ports API](/documents/api/server-and-cli).
