# Inspect CLI

## Purpose

The inspect CLI provides programmatic access to a running WebComPy application for automated testing, verification, and debugging. It bridges the gap between the framework's browser-based runtime and external tooling by offering structured JSON output for all commands. This enables CI pipelines, AI agents, and developers to launch servers, capture screenshots, collect console output, query DOM state, and assert expectations — all without manual browser interaction.

## Requirements

### Requirement: The inspect serve command shall launch a WebComPy app server as a subprocess on an auto-detected port
The `webcompy inspect serve` command SHALL start a WebComPy application server by launching `webcompy start` as a background subprocess. When `--port 0` is specified (the default), `serve` SHALL find a free port before starting the subprocess and pass it to `webcompy start --port N`. The PID file SHALL use this pre-detected port. The command SHALL output JSON containing the `port`, `url`, and `pid` of the server process. The `--config` flag SHALL accept an import path to a `WebComPyBuildConfig` instance, following the same discovery rules as `webcompy start` (i.e., `discover_config()`). The `--dev` flag SHALL enable hot-reload mode. The `--runtime-serving` flag SHALL accept `"cdn"` or `"local"` and override `WebComPyBuildConfig.runtime_serving`.

#### Scenario: Starting a server with auto-detected port
- **WHEN** a developer runs `webcompy inspect serve --config my_app.config`
- **THEN** the server SHALL start on an OS-assigned free port
- **AND** JSON output SHALL include `{"port": N, "url": "http://localhost:N/", "pid": P}`

#### Scenario: Starting a server with a specific port
- **WHEN** a developer runs `webcompy inspect serve --config my_app.config --port 8080`
- **THEN** the server SHALL start on port 8080
- **AND** JSON output SHALL include `{"port": 8080, "url": "http://localhost:8080/", "pid": P}`

#### Scenario: Starting a server in dev mode
- **WHEN** a developer runs `webcompy inspect serve --config my_app.config --dev`
- **THEN** the server SHALL start with hot-reload enabled
- **AND** `WebComPyServerConfig.dev` SHALL be `True`

#### Scenario: Starting a server with runtime-serving override
- **WHEN** a developer runs `webcompy inspect serve --config my_app.config --runtime-serving local`
- **THEN** `runtime_serving` SHALL be `"local"` for the session

#### Scenario: Starting a server using default config discovery
- **WHEN** a developer runs `webcompy inspect serve` without `--config`
- **AND** `webcompy_config.py` exists at the project root
- **THEN** the CLI SHALL discover the config using the same rules as `webcompy start`

### Requirement: The inspect serve command shall manage PID files for server lifecycle
The `serve` command SHALL write a PID file to `.tmp/webcompy-inspect/<port>.pid` containing JSON with `pid`, `port`, `url`, and `config_path`. The PID file directory SHALL be created if it does not exist. Stale PID files (where the process no longer exists) SHALL be cleaned up when `serve` encounters a conflicting port.

#### Scenario: PID file creation
- **WHEN** `serve` successfully starts a server on port N
- **THEN** a file at `.tmp/webcompy-inspect/N.pid` SHALL contain `{"pid": P, "port": N, "url": "http://localhost:N/", "config_path": "..."}`

#### Scenario: Cleaning up stale PID file
- **WHEN** `serve` finds a PID file for port N but the process no longer exists
- **THEN** the stale PID file SHALL be removed
- **AND** the server SHALL start normally on port N

### Requirement: The inspect stop command shall stop a running server
The `webcompy inspect stop` command SHALL accept a port number and terminate the server process associated with that port. It SHALL read the PID file, verify that the process with the stored PID is still running and is the expected server process (by checking the process command line matches the expected `webcompy start` invocation, or by verifying the process is listening on the expected port), send SIGTERM, wait for the process to exit (with a default timeout of 10 seconds, overridable via `--timeout`), and clean up the PID file.

#### Scenario: Stopping a running server
- **WHEN** a developer runs `webcompy inspect stop 8080` and a server is running on port 8080
- **THEN** the command SHALL verify the PID file exists and the process is still running
- **AND** the server process SHALL be terminated via SIGTERM
- **AND** the PID file SHALL be removed
- **AND** JSON output SHALL include `{"stopped": true, "port": 8080}`

#### Scenario: Stopping a non-existent server
- **WHEN** a developer runs `webcompy inspect stop 9999` and no server is running on port 9999
- **THEN** JSON output SHALL include `{"stopped": false, "port": 9999, "error": "No server found on port 9999"}`

#### Scenario: Stopping with custom timeout
- **WHEN** a developer runs `webcompy inspect stop 8080 --timeout 30`
- **THEN** the command SHALL wait up to 30 seconds for the process to exit

#### Scenario: Stopping with stale PID file
- **WHEN** a developer runs `webcompy inspect stop 8080`
- **AND** a PID file exists for port 8080 but the process no longer exists
- **THEN** the stale PID file SHALL be removed
- **AND** JSON output SHALL include `{"stopped": false, "port": 8080, "error": "No server found on port 8080"}`

### Requirement: The inspect screenshot command shall capture browser screenshots
The `webcompy inspect screenshot <url>` command SHALL launch a headless Chromium browser, navigate to the URL, and capture a screenshot. The `--selector` flag SHALL limit the screenshot to a specific CSS selector. The `--full-page` flag SHALL capture the entire scrollable page. The `--output` flag SHALL specify the output file path; if omitted, the screenshot SHALL be written to stdout as base64-encoded PNG data. The `--wait-for` flag SHALL accept a CSS selector and wait for it to appear before capturing.

#### Scenario: Full-page screenshot
- **WHEN** a developer runs `webcompy inspect screenshot http://localhost:8080/ --full-page --output page.png`
- **THEN** a PNG file named `page.png` SHALL be created containing the full scrollable page

#### Scenario: Element screenshot
- **WHEN** a developer runs `webcompy inspect screenshot http://localhost:8080/ --selector "#my-widget" --output widget.png`
- **THEN** a PNG file SHALL be created containing only the `#my-widget` element

#### Scenario: Waiting for element before screenshot
- **WHEN** a developer runs `webcompy inspect screenshot http://localhost:8080/ --wait-for "#webcompy-app" --output app.png`
- **THEN** the browser SHALL wait until `#webcompy-app` is visible before capturing
- **AND** the screenshot SHALL show the fully rendered application

### Requirement: The inspect console command shall collect browser console messages
The `webcompy inspect console <url>` command SHALL launch a headless Chromium browser, navigate to the URL, register a console message listener, collect messages for a configurable duration, and output them as JSON. The `--level` flag SHALL filter messages by severity (error, warning, info, log, debug), defaulting to `warning`. The default level of `warning` (which includes `error` and `warning`) is intentionally different from the E2E test file-level default of `debug` — the CLI default prioritizes actionable output for developers, while the E2E default prioritizes comprehensive logging for test diagnostics. The `--wait` flag SHALL specify the collection duration in milliseconds, defaulting to 5000. The `--wait-for` flag SHALL accept a CSS selector to wait for before starting collection.

#### Scenario: Collecting console errors and warnings
- **WHEN** a developer runs `webcompy inspect console http://localhost:8080/ --level warning`
- **THEN** JSON output SHALL include an array of messages with `type`, `text`, and `location` fields
- **AND** only messages with level `error` or `warning` SHALL be included

#### Scenario: Waiting for app initialization before collecting
- **WHEN** a developer runs `webcompy inspect console http://localhost:8080/ --wait-for "#webcompy-app"`
- **THEN** the browser SHALL wait until `#webcompy-app` is visible before starting the collection timer
- **AND** all messages from initialization SHALL be included in the output

### Requirement: The inspect query command shall retrieve DOM element properties
The `webcompy inspect query <url> <selector>` command SHALL launch a headless Chromium browser, navigate to the URL, and return properties of the matching element(s). The `--property` flag SHALL specify which property to return: `text` (default), `html`, `attr:NAME`, `visible`, or `count`. The `--wait-for` flag SHALL accept a CSS selector to wait for before querying.

#### Scenario: Querying element text
- **WHEN** a developer runs `webcompy inspect query http://localhost:8080/ "h1" --property text`
- **THEN** JSON output SHALL include `{"results": ["Hello World"]}`

#### Scenario: Querying element visibility
- **WHEN** a developer runs `webcompy inspect query http://localhost:8080/ "#webcompy-app" --property visible`
- **THEN** JSON output SHALL include `{"results": [true]}`

#### Scenario: Querying multiple elements
- **WHEN** a developer runs `webcompy inspect query http://localhost:8080/ "li" --property text`
- **AND** three `<li>` elements exist on the page
- **THEN** JSON output SHALL include `{"results": ["Item 1", "Item 2", "Item 3"]}`

### Requirement: The inspect click command shall click an element and optionally wait for state changes
The `webcompy inspect click <url> <selector>` command SHALL launch a headless Chromium browser, navigate to the URL, click the specified element, and optionally wait for a resulting state. The `--wait-for` flag SHALL accept a CSS selector to wait for after clicking.

#### Scenario: Clicking a button
- **WHEN** a developer runs `webcompy inspect click http://localhost:8080/ "#increment-btn"`
- **THEN** the button SHALL be clicked
- **AND** JSON output SHALL include `{"clicked": true, "selector": "#increment-btn"}`

#### Scenario: Clicking and waiting for result
- **WHEN** a developer runs `webcompy inspect click http://localhost:8080/ "#submit-btn" --wait-for ".success-message"`
- **THEN** the button SHALL be clicked
- **AND** the browser SHALL wait until `.success-message` is visible
- **AND** JSON output SHALL include `{"clicked": true, "selector": "#submit-btn", "wait_for": ".success-message", "appeared": true}`

### Requirement: The inspect navigate command shall navigate to a path and wait for readiness
The `webcompy inspect navigate <url> <path>` command SHALL launch a headless Chromium browser, navigate to the URL, then navigate to the specified path within the app, and wait for a readiness condition. The `--wait-for` flag SHALL accept a CSS selector to wait for.

#### Scenario: Navigating to a sub-page
- **WHEN** a developer runs `webcompy inspect navigate http://localhost:8080/ "/about" --wait-for "#about-page"`
- **THEN** the browser SHALL navigate to `http://localhost:8080/about`
- **AND** wait until `#about-page` is visible
- **AND** JSON output SHALL include `{"current_url": "http://localhost:8080/about", "title": "About"}`

### Requirement: The inspect verify command shall assert expectations about a page
The `webcompy inspect verify <url>` command SHALL launch a headless Chromium browser, navigate to the URL, and check one or more expectations. The `--expect` flag SHALL accept repeatable assertion strings. Each `--expect` value SHALL use one of the following syntaxes:
- `selector=expected_text` — assert that the element's text content equals `expected_text` (exact match)
- `selector*=partial_text` — assert that the element's text content contains `partial_text` (substring match)
- `selector:visible` — assert that the element is visible
- `selector:attr:name=value` — assert that the element's attribute `name` equals `value`
- `console:no-error` — assert that no error-level console messages were logged
- `console:no-level=LEVEL` — assert that no messages of the specified level were logged

The `--wait-for` flag SHALL accept a CSS selector to wait for before checking expectations. For `console:*` assertions, console messages SHALL be collected from page load until the `--wait-for` element becomes visible (or a default timeout of 5000ms if `--wait-for` is not specified), at which point collection ends and assertions are evaluated.

The command SHALL exit with code 0 if all expectations pass, and code 1 if any fail.

#### Scenario: Verifying element text (exact match)
- **WHEN** a developer runs `webcompy inspect verify http://localhost:8080/ --expect "h1=Hello World" --expect "#counter:visible"`
- **THEN** JSON output SHALL include `{"passed": ["h1=Hello World", "#counter:visible"], "failed": []}`
- **AND** exit code SHALL be 0

#### Scenario: Verification failure
- **WHEN** a developer runs `webcompy inspect verify http://localhost:8080/ --expect "h1=Goodbye"`
- **AND** the `h1` element contains "Hello World"
- **THEN** JSON output SHALL include `{"passed": [], "failed": [{"expect": "h1=Goodbye", "actual": "Hello World"}]}`
- **AND** exit code SHALL be 1

#### Scenario: Verifying console has no errors
- **WHEN** a developer runs `webcompy inspect verify http://localhost:8080/ --expect "console:no-error" --wait-for "#webcompy-app"`
- **THEN** the browser SHALL navigate to the URL, wait for `#webcompy-app`, collect console messages
- **AND** verify that no error-level messages were logged

### Requirement: Each inspect browser command shall launch an independent browser session
Each `inspect` command that interacts with a browser (`screenshot`, `console`, `query`, `click`, `navigate`, `verify`) SHALL launch a fresh headless Chromium browser instance, perform its operation, and close the browser before exiting. Browser sessions are NOT reused across separate `inspect` invocations. This ensures isolation between commands but means each command incurs browser startup latency.

#### Scenario: Running two consecutive inspect commands
- **WHEN** a developer runs `webcompy inspect screenshot http://localhost:8080/ --output a.png`
- **AND** then runs `webcompy inspect screenshot http://localhost:8080/ --output b.png`
- **THEN** each command SHALL launch its own browser instance
- **AND** the two browser instances SHALL be independent

### Requirement: The inspect command shall handle missing Playwright gracefully
When the `playwright` package is not installed, any `inspect` subcommand SHALL print a helpful error message suggesting installation commands and exit with code 1.

#### Scenario: Running inspect without Playwright installed
- **WHEN** a developer runs `webcompy inspect screenshot http://localhost:8080/`
- **AND** the `playwright` package is not installed
- **THEN** the command SHALL print an error message containing installation instructions
- **AND** exit with code 1