# Proposal: feat-docs-guides-tutorial

## Why

Getting Started proves the toolchain works but stops at a static heading; Basic Usage documents features individually. The missing rung (per the restructure plan) is a guided sequence that turns a blank project into a complete app, so a reader experiences feature interaction — the Vue/Angular "Tour of Heroes" / "first-app" role. This change creates the `Guides` category as that tutorial.

## What Changes

- Introduce the `Guides` section (inserted between Getting Started and Basic Usage) with an overview page and six steps building one **ToDo application**:
  1. `todo-app-shell` — project state: tasks in a `ReactiveList`, counters/filters via `use_state`/`use_computed` (app shell renders, no input yet)
  2. `todo-components` — extract `todo-item`/`todo-toolbar` components; props and slots
  3. `todo-navigation` — split list/archive pages with flat `Router` + `RouterLink` active state
  4. `todo-forms` — add task form with `use_field`/`use_form`, validators, UI form controls (`Input`, `Checkbox`) and `:bind`
  5. `todo-remote-data` — persist via `use_async_result` + `HttpClient` against `/api/tasks`, mocked with a `FetchMiddleware` in the demo app so it runs on static hosting too
  6. `todo-deploy` — `webcompy generate` to static output; what hydration baked vs runtime fetching means; next-steps pointers to Basic/Advanced pages
- Each step page: narrative + **live iframe demo of that step's state** + full source CodeBlock (copy of the step app), following the Examples presentation shape early.
- Tutorial demo apps live at `docs_app/static/_demos/todo_tutorial/<step>/app.py` registered in `standard.html`; the step-5 mock data lives entirely client-side via middleware (no server needed in either serving mode).
- E2E for the tutorial pages (titles, demo iframe loads, step-5 mocked fetch succeeds in static mode).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `docs-site-documents`: `Guides` category requirement — linear build-to-completion tutorial with per-step live demo and complete source; ordering and page set.

## Impact

- `docs_app/docs_manifest.py` (Guides section, 7 entries), 7 new `.md` + wrappers, 6 iframe apps + `standard.html` package list, `docs_app/documents/` new dir scope for pages, `e2e/docs/` new files
- No framework changes; reuses `DemoDisplay`/iframe-isolation pattern and the merge-middleware capability

## Known Issues Addressed

None.

## Non-goals

- Multiple tutorials or other subject apps (one canonical app)
- Real backend integration in the tutorial (the API layer is middleware-mocked; real ASGI/RPC patterns belong to Advanced pages and the migration guide)
- Rewriting the existing `/sample/todo` demo (tutorial apps are separate)
