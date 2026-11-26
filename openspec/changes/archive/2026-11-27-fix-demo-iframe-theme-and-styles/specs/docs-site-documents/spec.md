# Spec Delta

## MODIFIED Requirements

### Requirement: The Guides category shall be a linear build-to-completion tutorial

The `DOCS_SECTIONS` manifest SHALL contain a `Guides` section between `Getting Started` and `Basic Usage`, holding an overview page plus six sequential ToDo-application step pages at `/documents/guides/` paths: app shell with reactive state, component extraction, navigation, forms, remote data (served by an in-app `FetchMiddleware` mock so it works in static hosting), and deployment. Each step page SHALL render a live demo iframe of that step's complete standalone app (registered under `docs_app/static/_demos/todo_tutorial/`) and the step's full source, SHALL add only concepts defined in Getting Started or earlier steps, and every step demo SHALL apply list/button/surface styles across component boundaries (`TodoList` / app shell) with WCAG AA contrast in both light and dark themes.

#### Scenario: Step ordering and progression

- **WHEN** the manifest is validated
- **THEN** the Guides pages appear overview-first in step order, and Prev/Next walks the sequence naturally

#### Scenario: Step 5 works without a server

- **WHEN** the remote-data step demo runs on the statically generated site
- **THEN** the task list loads and submits succeed through the in-app middleware mock with no network errors in the console

#### Scenario: Curriculum containment

- **WHEN** a step page is reviewed
- **THEN** it uses only Basic-level APIs (no guards, middleware registries beyond the provided mock recipe, hydration internals, or other Advanced topics)

#### Scenario: Tutorial step demos preserve list styles and theme contrast

- **WHEN** `todo_tutorial/step3` through `todo_tutorial/step6` render inside `DemoDisplay` in light or dark mode
- **THEN** `.task-list` styles apply to the rendered task list child elements and all buttons/inputs maintain accessible theme contrast

### Requirement: The Examples category shall present explanation plus live demo plus source

The manifest SHALL contain an `Examples` category at `/documents/examples/`, with pages (in order): `hello-world`, `todo`, `forms`, `routing`, `storage-sync`, `transition`, `teleport`, `i18n-playground`, `matplotlib`, `http-fetch`, `fetch-middleware`, `rpc-middleware`. Each page SHALL combine a Markdown narrative, a live demo iframe of the showcase app, and the demo's full source; any page whose demo needs a backend SHALL satisfy it with an in-app `FetchMiddleware`/`RpcMiddleware` mock so it works identically on the dev server and the static export, and SHALL include a "real server wiring" section with server-side code and links to the corresponding Advanced pages. Every showcase demo SHALL follow the parent site's active light/dark theme tokens cleanly without unstyled child routes or vertical iframe clipping. The legacy `/sample/*` routes and the Navbar "Demos" dropdown SHALL be removed without redirects; `fizzbuzz` SHALL be retired entirely.

#### Scenario: Mocked networking works on static export

- **WHEN** the fetch-middleware or rpc-middleware example runs from the generated static site
- **THEN** its demo interactions complete successfully with no failed network requests in the console

#### Scenario: Sample routes removed

- **WHEN** `/sample/todo` is requested
- **THEN** the 404 page renders and the Navbar no longer exposes a Demos dropdown

#### Scenario: Example page trio present

- **WHEN** any Examples page is opened
- **THEN** it shows narrative, an embedded live demo, and the complete demo source

#### Scenario: Example live demos synchronize theme and size without clipping

- **WHEN** an Examples page is viewed in light or dark mode (including toggling live between them)
- **THEN** the embedded demo iframe adopts the active theme, renders all nested route views and controls cleanly with WCAG AA contrast, and sizes vertically without clipping content

## ADDED Requirements

### Requirement: Inline UI documentation demos SHALL render with visible dimensions and contrast

Interactive inline component previews on `/documents/basic/ui-primitives` (specifically `HeadlessSpinner`) SHALL have explicit visible dimensions and theme-aware stroke/border contrast so no preview collapses to `0×0px` or blends invisibly into its background.

#### Scenario: HeadlessSpinner preview is visibly rendered on ui-primitives page

- **WHEN** a user visits `/documents/basic/ui-primitives` in light or dark mode
- **THEN** the `HeadlessSpinner` preview element SHALL have non-zero width and height (`> 0px`) and visible contrast against its card surface
