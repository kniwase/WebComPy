## ADDED Requirements

### Requirement: The inspect serve command shall launch a WebComPy app on an auto-detected port
The `webcompy inspect serve` command SHALL start a WebComPy application server. When `--port 0` is specified (the default), the server SHALL bind to an OS-assigned free port. The command SHALL output JSON containing the `port`, `url`, and `pid` of the server process. The `--app` flag SHALL accept an import path to the `WebComPyApp` instance (e.g., `my_app.app:app`). The `--config` flag SHALL accept an import path to a `WebComPyBuildConfig` instance, following the same discovery rules as `webcompy start`. The server SHALL be started as a background subprocess. The `--dev` flag SHALL enable hot-reload mode.

#### Scenario: Starting a server with auto-detected port
- **WHEN** a developer runs `webcompy inspect serve --app my_app.app:app`
- **THEN** the server SHALL start on an OS-assigned free port
- **AND** JSON output SHALL include `{"port": N, "url": "http://localhost:N/", "pid": P}`

#### Scenario: Starting a server with a specific port
- **WHEN** a developer runs `webcompy inspect serve --app my_app.app:app --port 8080`
- **THEN** the server SHALL start on port 8080
- **AND** JSON output SHALL include `{"port": 8080, "url": "http://localhost:8080/", "pid": P}`

#### Scenario: Starting a server in dev mode
- **WHEN** a developer runs `webcompy inspect serve --app my_app.app:app --dev`
- **THEN** the server SHALL start with hot-reload enabled
- **AND** `WebComPyServerConfig.dev` SHALL be `True`

### Requirement: The inspect serve command shall manage PID files for server lifecycle
The `serve` command SHALL write a PID file to `.tmp/webcompy-inspect/<port>.pid` containing JSON with `pid`, `port`, `url`, and `app_path`. The PID file directory SHALL be created if it does not exist. Stale PID files (where the process no longer exists) SHALL be cleaned up when `serve` encounters a conflicting port.

#### Scenario: PID file creation
- **WHEN** `serve` successfully starts a server on port N
- **THEN** a file at `.tmp/webcompy-inspect/N.pid` SHALL contain `{"pid": P, "port": N, "url": "http://localhost:N/", "app_path": "..."}`

#### Scenario: Cleaning up stale PID file
- **WHEN** `serve` finds a PID file for port N but the process no longer exists
- **THEN** the stale PID file SHALL be removed
- **AND** the server SHALL start normally on port N

### Requirement: The inspect stop command shall stop a running server
The `webcompy inspect stop` command SHALL accept a port number and terminate the server process associated with that port. It SHALL read the PID file, send SIGTERM, wait for the process to exit (with a timeout), and clean up the PID file.

#### Scenario: Stopping a running server
- **WHEN** a developer runs `webcompy inspect stop 8080` and a server is running on port 8080
- **THEN** the server process SHALL be terminated
- **AND** the PID file SHALL be removed
- **AND** JSON output SHALL include `{"stopped": true, "port": 8080}`

#### Scenario: Stopping a non-existent server
- **WHEN** a developer runs `webcompy inspect stop 9999` and no server is running on port 9999
- **THEN** JSON output SHALL include `{"stopped": false, "port": 9999, "error": "No server found on port 9999"}`

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
The `webcompy inspect console <url>` command SHALL launch a headless Chromium browser, navigate to the URL, register a console message listener, collect messages for a configurable duration, and output them as JSON. The `--level` flag SHALL filter messages by severity (error, warning, info, log, debug), defaulting to `warning`. The `--wait` flag SHALL specify the collection duration in milliseconds, defaulting to 5000. The `--wait-for` flag SHALL accept a CSS selector to wait for before starting collection.

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
The `webcompy inspect verify <url>` command SHALL launch a headless Chromium browser, navigate to the URL, and check one or more expectations. The `--expect` flag SHALL accept repeatable assertion strings in the format `selector:text`, `selector:visible`, `selector:attr:name=value`, or `console:level=error`. The command SHALL exit with code 0 if all expectations pass, and code 1 if any fail.

#### Scenario: Verifying element text
- **WHEN** a developer runs `webcompy inspect verify http://localhost:8080/ --expect "h1=Hello World" --expect "#counter:visible"`
- **THEN** JSON output SHALL include `{"passed": ["h1=Hello World", "#counter:visible"], "failed": []}`
- **AND** exit code SHALL be 0

#### Scenario: Verification failure
- **WHEN** a developer runs `webcompy inspect verify http://localhost:8080/ --expect "h1=Goodbye"`
- **AND** the `h1` element contains "Hello World"
- **THEN** JSON output SHALL include `{"passed": [], "failed": [{"expect": "h1=Goodbye", "actual": "Hello World"}]}`
- **AND** exit code SHALL be 1

#### Scenario: Verifying console has no errors
- **WHEN** a developer runs `webcompy inspect verify http://localhost:8080/ --expect "console:level=error" --wait-for "#webcompy-app"`
- **THEN** the browser SHALL navigate to the URL, wait for `#webcompy-app`, collect console messages
- **AND** verify that no error-level messages were logged

### Requirement: The inspect command shall handle missing Playwright gracefully
When the `playwright` package is not installed, any `inspect` subcommand SHALL print a helpful error message suggesting installation commands and exit with code 1.

#### Scenario: Running inspect without Playwright installed
- **WHEN** a developer runs `webcompy inspect screenshot http://localhost:8080/`
- **AND** the `playwright` package is not installed
- **THEN** the command SHALL print an error message containing installation instructions
- **AND** exit with code 1

## MODIFIED Requirements

### Requirement: The CLI shall accept --runtime-serving value flag
The `start`, `generate`, and `inspect serve` CLI subcommands SHALL accept `--runtime-serving <mode>` where `<mode>` is `"cdn"` or `"local"`. This overrides `WebComPyBuildConfig.runtime_serving`.

#### Scenario: Overriding with --runtime-serving local for inspect serve
- **WHEN** a developer runs `webcompy inspect serve --app my_app.app:app --runtime-serving local`
- **THEN** `runtime_serving` SHALL be `"local"` for the session