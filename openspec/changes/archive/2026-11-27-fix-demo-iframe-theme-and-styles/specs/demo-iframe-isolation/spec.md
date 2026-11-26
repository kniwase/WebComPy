# Spec Delta

## ADDED Requirements

### Requirement: Demo iframes SHALL load framework design tokens and synchronize with parent theme changes

The `docs_app/static/_demos/standard.html` shell SHALL load the framework design tokens/base stylesheet (`/_webcompy-ui/index.css`) and mirror the active theme from its same-origin parent document (reading the parent `<style data-webcompy-dynamic>` rule on startup and watching parent style updates via `MutationObserver`, with `webcompy-theme` cookie fallback when opened directly). Both the `#webcompy-loading` screen and the mounted demo app SHALL react immediately when the user toggles the parent site's theme between light, dark, and system modes.

#### Scenario: Live parent theme toggle updates mounted demo iframe

- **WHEN** a user views any docs page with an embedded `/_demos/standard.html?app=...` iframe and toggles the site theme from light to dark (or dark to light)
- **THEN** the iframe's `<style data-webcompy-dynamic>` rule SHALL update automatically to match the parent document without reloading the iframe
- **AND** background, text, border, and form-control colors inside the iframe SHALL switch cleanly to the newly selected theme

#### Scenario: Opening standard.html standalone falls back cleanly

- **WHEN** `standard.html?app=helloworld` is opened without a same-origin parent frame
- **THEN** it SHALL still initialize using `/_webcompy-ui/index.css` and `webcompy-theme` / OS preference without raising JavaScript errors

### Requirement: Demo apps SHALL honor design tokens and fix cross-component scoped styling boundaries

All demo apps under `docs_app/static/_demos/` SHALL derive surface, text, border, and accent colors from theme CSS variables (or define explicit light/dark-safe tokens matching WCAG 2.1 AA contrast `>= 4.5:1`) and SHALL NOT pass parent-only `scoped_style` classes across component `webcompy-cid` boundaries where child components or slotted subtrees would remain unstyled. Furthermore, the `routing` demo SHALL display a non-empty root path (`"/"`) on initial load and style its child route panels cleanly.

#### Scenario: Interactive demos remain legible in dark and OS-inverted themes

- **WHEN** `fetch_sample`, `transition`, `storage_sync`, `todo`, `teleport`, `matplotlib_sample`, `ui_form_controls`, `rpc_middleware_mock`, `fetch_middleware_mock`, `i18n_playground`, and `todo_tutorial/step1..step6` render inside an iframe under both light and dark modes (across OS light and OS dark preferences)
- **THEN** all readable text, status badges, buttons, inputs, modals, and dropdowns SHALL maintain at least 4.5:1 foreground-to-background contrast

#### Scenario: Cross-component styles apply to child routes, slots, and task lists

- **WHEN** `routing` child route views, `migration_users` slotted directory cards/rows, and `todo_tutorial/step3..step6` task lists render in a browser
- **THEN** the rendered elements SHALL carry matching scoped styles on their owning components (or shared demo stylesheet) rather than silently failing due to parent `webcompy-cid` attribute mismatch

### Requirement: Demo iframes SHALL size responsively without vertical clipping

`DemoDisplay` in `docs_app` SHALL size embedded demo iframes based on measured demo content height (via safe same-origin `ResizeObserver` / height synchronization capped/scrolled gracefully on narrow viewports) or sufficient per-demo minimum height so interactive demos taller than `400px` (`forms`, `http-fetch`, `matplotlib_sample`, `i18n-playground`, `migration_users`) are not clipped on initial render.

#### Scenario: Tall demo iframes expand to fit their content

- **WHEN** a user opens `/documents/examples/forms` or `/documents/examples/http-fetch`
- **THEN** the embedded `<iframe>` height SHALL accommodate the rendered demo UI without clipping primary controls below `400px`
