# Proposal: feat-docs-examples

## Why

The `/sample/*` demo pages show an iframe and raw source but explain nothing — readers see code without the "why". Meanwhile the demo set drifted arbitrarily (FizzBuzz teaches little the ToDo app doesn't) and important framework features (routing patterns, storage sync, middleware-driven offline mocks) have no demo at all. Turning demos into an `Examples` category — explanation + code + live app as one page — fulfills the docs system's hands-on layer, and middleware mocks (design decision of ③-2/③-3) make every example work on the static site too.

## What Changes

- Create the `Examples` standalone category (`/documents/examples/`): each page = Markdown narrative (what it demonstrates, key mechanisms, how to adapt) + live iframe demo + full source, replacing today's bare `/sample/*` pages. **BREAKING** for docs URLs: all `/sample/*` routes are removed (no redirects), Navbar "Demos" dropdown replaced by the Examples category.
- Migrate and write explanations for existing demos: `hello-world`, `todo`, `matplotlib`, `http-fetch`, `teleport`, `transition`, `form-controls`, `i18n-playground`.
- **Retire FizzBuzz**: its list/reactivity coverage moves into the ToDo narrative; the demo app and page are deleted.
- Add new demos: `routing` (nested routes + guard redirect), `storage-sync` (cross-tab `sync_tabs`), `fetch-middleware` (mocked endpoint via `FetchMiddleware`), `rpc-middleware` (contract-first RPC served by an in-app `RpcMiddleware` mock; page also shows the real server-side registration for reference).
- E2E: per-page dedicated tests; the stale "skip fetch demo until sample.json exists" requirement is removed (the file has existed since #237 as `sample_object.json`); interactive scenarios re-point to the examples URLs (forms submit, todo add, matplotlib increment).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `docs-site-documents`: Examples category (page set, page shape with narrative + live demo + source, middleware-mock rule for networked demos, removal of `/sample`).
- `docs-e2e`: dedicated-test-file route examples and interactivity scenarios updated to Examples URLs; obsolete fetch-skip requirement removed.

## Impact

- `docs_app/pages/demo/` + `docs_app/router.py` (routes removed), `docs_app/layout.py` (Navbar Demos entry removed), new `docs_app/documents/examples/*.md` + pages/wrappers + manifest category, `docs_app/static/_demos/` (fizzbuzz removed; new routing/storage/fetch-mock/rpc-mock apps added; `standard.html` map updated), `e2e/docs/` file renames + updates
- No package changes

## Known Issues Addressed

Closes the docs-e2e stale skip ("Fetch demo test shall be skipped until sample.json is available") by deleting the skip rule when its premise was already met upstream.

## Non-goals

- Tutorial rewrites (Guides ③-3 owns the step-by-step app); Examples are single-feature showcases
- Hosting real RPC endpoints in docs_app (mocks suffice for both serving modes; real server patterns stay in ③-4/③-6 pages)
- New framework features
