# Delta: port-abstraction

## ADDED Requirements

### Requirement: HistoryPort shall own browser URL updates

`HistoryPort` SHALL provide `push_url(path, state)` and `replace_url(path, state)` methods. The base implementations SHALL be no-ops (server environments perform no URL manipulation). `BrowserHistoryPort` SHALL implement them via `window.history.pushState` / `replaceState`, building the browser-visible URL from the app-internal path by applying the router mode (`#` prefix in hash mode) and the app `base_url` prefix in history mode; to support this, `BrowserHistoryPort` SHALL accept an optional `base_url` constructor parameter. Non-JSON-serializable `state` SHALL be passed as `None` to the browser with a logged warning. Testing fakes SHOULD record invocations for assertions.

#### Scenario: History-mode URL building
- **GIVEN** a `BrowserHistoryPort` in history mode with `base_url="/myapp"`
- **WHEN** `push_url("/about", None)` is called
- **THEN** the browser history SHALL receive the URL `/myapp/about/`

#### Scenario: Hash-mode URL building
- **GIVEN** a `BrowserHistoryPort` in hash mode
- **WHEN** `push_url("/about", None)` is called
- **THEN** the browser history SHALL receive the URL `#/about/`

#### Scenario: Server no-op
- **WHEN** `push_url` is called on a server history port during SSR/SSG
- **THEN** no browser API SHALL be accessed and no error SHALL occur

#### Scenario: Redirect uses replace
- **WHEN** the navigation pipeline commits a redirect
- **THEN** `replace_url` SHALL be called instead of `push_url`
