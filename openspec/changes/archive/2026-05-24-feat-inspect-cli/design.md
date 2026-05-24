## Context

WebComPy's existing E2E test infrastructure uses Playwright via pytest fixtures to start servers, navigate to pages, and capture console messages. This works well for CI but is inaccessible outside the test suite. Developers and coding agents need a CLI-based way to:

1. Launch a WebComPy app on a free port
2. Navigate to it in a real browser
3. Capture screenshots, console output, and DOM state
4. Make assertions about the application's behavior

The `inspect` CLI subcommand bridges this gap by exposing these capabilities as standalone commands that output structured JSON.

## Goals / Non-Goals

**Goals:**
- Provide a CLI interface for launching/stopping WebComPy apps with auto-port-detection
- Enable browser inspection (screenshots, console logs, DOM queries) from the command line
- Support automated verification assertions for coding agents
- Output structured JSON for programmatic consumption
- Reuse the same Playwright browser infrastructure as E2E tests

**Non-Goals:**
- MCP server implementation (future change)
- Replacing or modifying the existing E2E test infrastructure
- Remote browser support (only local Chromium)
- Interactive REPL debugging
- Network request interception (available via Playwright MCP)
- Browser session reuse across `inspect` invocations (each command starts a fresh browser)

## Decisions

### D1: Playwright as the browser automation engine

**Decision**: Use `playwright.sync_api` directly, same as the E2E tests.

**Alternatives considered**:
- Selenium: Heavier setup, less Python-native API
- puppeteer (via pyppeteer): Less maintained, API drift from Node version

**Rationale**: Playwright is already a project dependency (dev group), the team is familiar with its API from E2E tests, and it provides the exact capabilities needed (console capture, screenshots, selectors).

### D2: CLI subcommand under `webcompy inspect`

**Decision**: Add all inspection commands as subcommands of `webcompy inspect` (e.g., `webcompy inspect serve`, `webcompy inspect screenshot`).

**Alternatives considered**:
- Top-level commands (`webcompy screenshot`): Too many top-level commands, poor grouping
- Separate `webcompy-inspect` package: Unnecessary packaging overhead

**Rationale**: Groups all inspection-related commands logically. Follows the pattern of `webcompy start` and `webcompy generate`.

### D3: JSON output for all commands

**Decision**: All commands output JSON to stdout. Errors output JSON with an `error` field.

**Rationale**: Structured output enables programmatic consumption by coding agents, shell scripts, and future MCP wrappers. JSON is universally parseable.

### D4: Server process management via PID files

**Decision**: `serve` writes a PID file to `.tmp/webcompy-inspect/<port>.pid` containing the process PID, port, and URL. `stop` reads this file to terminate the server. `serve` launches `webcompy start` as a subprocess. When `--port 0` is specified, `serve` finds a free port first (using the same approach as the E2E test script's `_find_free_port()`) and passes it to `webcompy start --port N`.

**Alternatives considered**:
- Process group management (pgid): Less portable, harder to clean up
- TCP port-based discovery: Race conditions, can't distinguish our servers from others

**Rationale**: PID files are simple, portable, and allow clean shutdown. The `.tmp/webcompy-inspect/` directory follows the project convention of using `.tmp/` for temporary files. Launching `webcompy start` as a subprocess reuses the existing server infrastructure.

### D5: Console message collection with Playwright page.on("console")

**Decision**: Reuse the same `ConsoleMessage` dataclass pattern from the E2E conftest for consistency.

**Rationale**: Same type/level hierarchy (error, warning, info, log, debug), same structured format (`[type] text (location)`). Code can potentially be shared in the future.

### D6: Playwright as optional dependency for inspect commands

**Decision**: Import `playwright` only when an `inspect` subcommand is invoked. If missing, print a helpful error suggesting `uv sync --group dev` or `pip install playwright`.

**Rationale**: Production deployments don't need Playwright. The `inspect` command is a developer tool. Keeping it optional reduces the core dependency footprint.

### D7: Independent browser sessions per command

**Decision**: Each `inspect` browser command (`screenshot`, `console`, `query`, `click`, `navigate`, `verify`) launches a fresh headless Chromium instance, performs its operation, and closes the browser before exiting.

**Rationale**: Simplifies implementation, ensures isolation between commands, and avoids state leakage. Browser startup latency is accepted as inherent — `serve` keeps the server running so multiple `inspect` calls can target it without restarting the app.

### D8: `--config` flag for app discovery (not `--app`)

**Decision**: `inspect serve` uses `--config` for app discovery, following the same pattern as `webcompy start` and `webcompy generate`. The `--app` flag is not used, as it has been removed from the CLI in favor of `--config` + `discover_config()`.

**Rationale**: Consistency with the existing CLI design. `discover_config()` handles both `--config <path>` and auto-discovery of `webcompy_config.py`.

### D9: `--expect` assertion syntax for verify

**Decision**: The `--expect` flag uses the following syntax:
- `selector=text` — exact text match
- `selector*=text` — substring match
- `selector:visible` — visibility check
- `selector:attr:name=value` — attribute check
- `console:no-error` — assert no error-level console messages
- `console:no-level=LEVEL` — assert no messages at the specified level

**Rationale**: The `=`/`*=` distinction makes exact vs. substring matching explicit. The `no-error` and `no-level=LEVEL` prefixes clearly express negation (asserting absence), which aligns with the most common verification need (no errors in console).

## Risks / Trade-offs

- **[Playwright installation required]** → Mitigate with clear error message suggesting `uv run playwright install chromium`
- **[Port race condition]** → Mitigate by pre-detecting a free port before starting the subprocess (same approach as E2E test script's `_find_free_port()`), then passing it to `webcompy start --port N`. TOCTOU race is accepted as inherent but unlikely in practice
- **[Stale PID files]** → Mitigate by checking process existence before relying on PID files; clean up on `stop`
- **[Browser startup latency]** → Accept as inherent; each command launches a fresh browser session. `serve` and `stop` are separate commands so the server stays running across multiple `inspect` calls
- **[Console message collection timing]** → `console` command accepts `--wait` parameter (default 5s) to allow PyScript initialization to complete before collecting
- **[PID reuse by unrelated processes]** → Mitigate by verifying the process command line matches the expected `webcompy start` invocation (via `psutil` or `/proc/<pid>/cmdline`), or by verifying the process is listening on the expected port
