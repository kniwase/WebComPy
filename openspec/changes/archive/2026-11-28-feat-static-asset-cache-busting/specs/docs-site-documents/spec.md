# Spec Delta

## MODIFIED Requirements

### Requirement: Docs site SHALL provide accessible landmarks, language attribute, controls, and heading hierarchy

`docs_app` SHALL emit `<html lang="en">` via `set_html_attr`, render a keyboard-focusable skip-to-content link targeting the main content landmark with its visually-hidden-until-focused styles inlined in `DocsRoot.scoped_style` (never relying solely on an external stylesheet), provide distinct `aria-label` attributes on navigation landmarks (primary navbar, docs sidebar, table of contents, Prev/Next pagination), use a semantic `RouterLink` home link for `.navbar-brand`, implement `ThemeToggle` as a standard cycle `<button>` with accessible SVG icon and live state `aria-label` (never a 2-state `role="switch"`), maintain sequential `H1 -> H2` heading hierarchy across `DemoDisplay` example sections, and render the `404` page with centered layout and direct recovery links to Home and Documentation. Furthermore, `/documents/basic/ui-primitives`, `/documents/basic/overlay`, and `/documents/basic/disclosure` SHALL position their live interactive demo sections ahead of `Next steps`.

#### Scenario: Automated accessibility landmark and control audit passes

- **WHEN** any docs_app page HTML/DOM is inspected
- **THEN** `<html lang="en">`, a skip link hidden off-screen until focused via inline `DocsRoot` scoped styles, uniquely labeled `<nav>` landmarks, a clickable home brand link, a non-`switch` `ThemeToggle` button, and monotonic heading levels are present

#### Scenario: Not Found page offers recovery navigation

- **WHEN** a user lands on an unmatched URL rendering `NotFound`
- **THEN** the page displays a structured card with links back to Home (`/`) and Getting Started (`/documents/getting-started/what-is-webcompy`)

## ADDED Requirements

### Requirement: Docs site SHALL ship static hosting cache headers for immutable runtime and wheel assets

`docs_app/static/_headers` SHALL declare `Cache-Control: public, max-age=31536000, immutable` for `/_webcompy-assets/*` and `/_webcompy-app-package/*` so static deployments copy `_headers` to the output root and cache versioned runtime bundles and content-hashed wheels without overriding revalidation on HTML pages or unhashed static files.

#### Scenario: Generated docs output includes static cache header rules

- **WHEN** `webcompy generate` runs for `docs_app`
- **THEN** `dist/_headers` SHALL exist and configure `public, max-age=31536000, immutable` for `/_webcompy-assets/*` and `/_webcompy-app-package/*`
