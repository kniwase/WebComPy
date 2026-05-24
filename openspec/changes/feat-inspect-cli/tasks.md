## 1. Project Setup

- [ ] 1.1 Create `webcompy/cli/_inspect.py` module with empty subcommand stubs and Playwright availability check
- [ ] 1.2 Register `inspect` subcommand group in `webcompy/cli/__init__.py`
- [ ] 1.3 Verify that `.tmp/*` in `.gitignore` already covers `.tmp/webcompy-inspect/`

## 2. Server Management (serve / stop)

- [ ] 2.1 Implement `inspect serve` command: pre-detect free port when `--port 0`, launch `webcompy start --port N` subprocess via `discover_config()`, write PID file, output JSON
- [ ] 2.2 Implement `inspect stop` command: read PID file, verify process identity (command line or port check), SIGTERM, wait with `--timeout` (default 10s), clean up PID file, output JSON
- [ ] 2.3 Add `--dev`, `--port`, `--config`, and `--runtime-serving` flags to `inspect serve`
- [ ] 2.4 Handle stale PID files and port conflicts in `serve`

## 3. Browser Inspection Commands

- [ ] 3.1 Implement shared Playwright browser launch helper with `--wait-for` support
- [ ] 3.2 Implement `inspect screenshot` command with `--selector`, `--full-page`, `--output`, `--wait-for` flags
- [ ] 3.3 Implement `inspect console` command with `--level` (default `warning`), `--wait`, `--wait-for` flags; reuse `ConsoleMessage` pattern from E2E conftest
- [ ] 3.4 Implement `inspect query` command with `--property` (text, html, attr:NAME, visible, count) and `--wait-for` flags
- [ ] 3.5 Implement `inspect click` command with `--wait-for` flag
- [ ] 3.6 Implement `inspect navigate` command with `--wait-for` flag
- [ ] 3.7 Implement `inspect verify` command with repeatable `--expect` assertions (`selector=text`, `selector*=text`, `selector:visible`, `selector:attr:name=value`, `console:no-error`, `console:no-level=LEVEL`) and exit code 0/1

## 4. Error Handling and Polish

- [ ] 4.1 Add graceful error handling for missing Playwright (helpful install message)
- [ ] 4.2 Add type annotations throughout `_inspect.py`
- [ ] 4.3 Add `inspect` CLI reference to AGENTS.md

## 5. Spec Updates

- [ ] 5.1 Update `openspec/specs/cli/spec.md` to include the `inspect serve` `--runtime-serving` flag addition
- [ ] 5.2 Update `.opencode/agents/ci-review.md` file→spec mapping to include `inspect-cli`