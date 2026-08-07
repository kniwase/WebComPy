# Delta: router

## MODIFIED Requirements

### Requirement: The router shall synchronize the browser URL with displayed content
When the URL changes — whether through user navigation (clicking links, using browser back/forward) or programmatic navigation — the router SHALL determine which page component to display and render it.

For app-initiated navigations, `RouterLink` activation SHALL call `Router.__set_path__()` without directly invoking `window.history.pushState`; the browser URL update SHALL be performed by the navigation pipeline after guards pass (see `router-hooks`): pushed for normal navigations, replaced for redirects. The anchor's `href` attribute generation SHALL be unchanged, so open-in-new-tab, copy-link, and SSR-rendered links behave identically. Validation of `params`/`query` argument shapes on activation SHALL be preserved, and non-JSON-serializable `params` SHALL log a warning with history state set to `None`.

#### Scenario: Clicking a navigation link
- **WHEN** a user clicks a `RouterLink`
- **THEN** the browser URL SHALL update without a full page reload
- **AND** the page component matching the new URL SHALL replace the currently displayed page

#### Scenario: Using browser back/forward buttons
- **WHEN** a user presses the browser back button
- **THEN** the router SHALL detect the URL change via `popstate`
- **AND** the previously displayed page component SHALL be restored

#### Scenario: Cancelled navigation leaves address bar unchanged
- **WHEN** a guard cancels a `RouterLink` navigation to `/admin`
- **THEN** the browser address bar SHALL remain on the current URL

#### Scenario: Programmatic navigation updates address bar
- **WHEN** app code calls `app.set_path("/about")` and guards pass
- **THEN** the browser address bar SHALL show the `/about` URL

#### Scenario: Anchor href unchanged
- **WHEN** a `RouterLink` is rendered
- **THEN** its `href` attribute SHALL be generated exactly as before (mode prefix, base_url, query encoding)
