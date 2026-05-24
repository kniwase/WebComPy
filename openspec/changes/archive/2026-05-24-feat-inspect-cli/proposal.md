## Why

WebComPy applications run in the browser via PyScript, making their runtime behavior difficult to inspect from the command line. Developers and coding agents currently lack a programmatic way to launch a WebComPy app, capture browser console output, take screenshots, and verify DOM state — all from a single CLI invocation. The existing E2E test infrastructure captures console messages via Playwright, but this capability is locked inside pytest fixtures and cannot be used outside of the test suite. An `inspect` CLI subcommand would unlock automated debugging, UI verification, and spike implementation validation for both developers and AI agents.

## What Changes

- Add a new `webcompy inspect` CLI subcommand with the following actions:
  - `serve`: Launch a WebComPy app server as a `webcompy start` subprocess on an auto-detected free port, outputting JSON with the URL and PID
  - `stop`: Stop a previously launched server by port, verifying the PID before sending SIGTERM, with a configurable timeout (default 10 seconds)
  - `screenshot`: Navigate to a URL and capture a screenshot (full page or element)
  - `console`: Navigate to a URL, collect browser console messages for a configurable duration, and output them as JSON
  - `query`: Navigate to a URL and retrieve DOM element properties (text, HTML, attributes, visibility)
  - `click`: Navigate to a URL, click an element, and optionally wait for a resulting state
  - `navigate`: Navigate to a URL path and wait for a selector or timeout
  - `verify`: Navigate to a URL and assert expectations (element text, visibility, console levels, URL)
- All commands output structured JSON for programmatic consumption
- The `serve` command uses port 0 (OS-assigned) by default to avoid conflicts
- The `serve` command accepts `--config` for app discovery (same as `webcompy start`), `--dev`, `--port`, and `--runtime-serving` flags
- The `stop` command accepts `--timeout` flag (default 10 seconds)
- The `console` command reuses the `ConsoleMessage` dataclass pattern from the E2E conftest
- The `verify` command uses `--expect` with syntax: `selector=text` (exact), `selector*=text` (contains), `selector:visible`, `selector:attr:name=value`, `console:no-error`, `console:no-level=LEVEL`
- Each browser command launches an independent browser session (no reuse across invocations)
- Server process management uses PID files under `.tmp/webcompy-inspect/`

## Capabilities

### New Capabilities
- `inspect-cli`: CLI tool for launching, inspecting, and verifying WebComPy applications in a real browser

### Modified Capabilities
- `cli`: The CLI module gains a new `inspect` subcommand group, including `--runtime-serving` support for `inspect serve`

## Impact

- `webcompy/cli/`: New `_inspect.py` module with subcommand implementations
- `webcompy/cli/__init__.py`: Register `inspect` subcommand
- Dependencies: `playwright` becomes a required dependency for `inspect` subcommands (already a dev dependency; may need conditional import or optional group)
- `.tmp/webcompy-inspect/`: New temporary directory for PID files and logs
- No breaking changes to existing CLI commands

## Known Issues Addressed

None — this is a new capability, not a fix.

## Non-goals

- MCP server implementation (will be a separate change)
- Replacing the existing E2E test infrastructure
- Supporting remote browser instances (only local Chromium via Playwright)
- Interactive debugging (REPL mode)
- Browser session reuse across `inspect` invocations (each command starts a fresh browser)