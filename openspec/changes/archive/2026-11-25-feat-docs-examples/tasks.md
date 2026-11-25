# Tasks: feat-docs-examples

## 1. Category and shared shape

- [x] 1.1 Add `examples_page_template(doc, demo_app)` in docs_app components (narrative + DemoDisplay section + source) and the Examples manifest category (`/documents/examples/`) with 12 entries in design order
- [x] 1.2 Add `routing`, `storage_sync`, `fetch_middleware_mock`, `rpc_middleware_mock` iframe apps under `static/_demos/` and register in `standard.html`

## 2. Migrated examples (explanations)

- [x] 2.1 Write hello-world, todo, forms, matplotlib pages (retire fizzbuzz: delete app dir, pages, tests; absorb its beats into the todo narrative)
- [x] 2.2 Write teleport, transition, i18n-playground, http-fetch pages

## 3. New examples

- [x] 3.1 Write routing (nested demo + guard redirect) and storage-sync (two-tab recipe) pages + apps
- [x] 3.2 Write fetch-middleware page: demo app intercepts `/api/*` via `FetchMiddleware`; narrative + real-server wiring section
- [x] 3.3 Write rpc-middleware page: contract-first demo answered by in-app `RpcMiddleware` typed synthesis; server-side `Procedure` registration shown; "real wiring" links to ③-4/③-6 pages

## 4. Removal and spec follow-through

- [x] 4.1 Delete `/sample/*` routes, page components, Navbar "Demos" dropdown entry, and stale e2e files; update cross-references from Home feature cards/README docs links
- [x] 4.2 docs-e2e follow-through: new `e2e/docs/test_examples_*.py` files (dedicated per page), interactivity + no-server scenarios, delete the fetch skip marker

## 5. Verification

- [x] 5.1 `ruff`/`pyright`/unit + `webcompy generate` + docs E2E groups (prod + static — mock pages must pass static) + `check-doc-spec-refs.py` + `openspec validate feat-docs-examples`
