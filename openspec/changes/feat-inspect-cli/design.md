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

**Decision**: `serve` writes a PID file to `.tmp/webcompy-inspect/<port>.pid` containing the process PID, port, and URL. `stop` reads this file to terminate the server.

**Alternatives considered**:
- Process group management (pgid): Less portable, harder to clean up
- TCP port-based discovery: Race conditions, can't distinguish our servers from others

**Rationale**: PID files are simple, portable, and allow clean shutdown. The `.tmp/webcompy-inspect/` directory follows the project convention of using `.tmp/` for temporary files.

### D5: Console message collection with Playwright page.on("console")

**Decision**: Reuse the same `ConsoleMessage` dataclass pattern from the E2E conftest for consistency.

**Rationale**: Same type/level hierarchy (error, warning, info, log, debug), same structured format (`[type] text (location)`). Code can potentially be shared in the future.

### D6: Playwright as optional dependency for inspect commands

**Decision**: Import `playwright` only when an `inspect` subcommand is invoked. If missing, print a helpful error suggesting `uv sync --group dev` or `pip install playwright`.

**Rationale**: Production deployments don't need Playwright. The `inspect` command is a developer tool. Keeping it optional reduces the core dependency footprint.

## Risks / Trade-offs

- **[Playwright installation required]** → Mitigate with clear error message suggesting `uv run playwright install chromium`
- **[Port race condition]** → Mitigate by using port 0 (OS-assigned) and reading the actual port from the server log
- **[Stale PID files]** → Mitigate by checking process existence before relying on PID files; clean up on `stop`
- **[Browser startup latency]** → Accept as inherent; `serve` and `stop` are separate commands so the browser session can be reused across multiple `inspect` calls
- **[Console message collection timing]** → `console` command accepts `--wait` parameter (default 5s) to allow PyScript initialization to complete before collecting