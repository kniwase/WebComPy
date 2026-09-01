# Tasks: feat-docs-advanced-integration

## 1. Core architecture pages

- [ ] 1.1 Write `dependency_injection_deep_dive.md` (scope tree, per-render-context isolation, port provisioning, test scopes/helpers; service + fake recipe) + wrapper + manifest (group)
- [ ] 1.2 Write `middleware.md` (chain ordering, registries, `next(request)` vs `next(..., response=...)`, streaming header-commit, plugin hook aggregation, hydration delegation; recipes: auth header, cache logger, offline mock)
- [ ] 1.3 Write `routing_deep_dive.md` (nested children, RouterView depth + level reuse rules, lazy/preload, guards & redirects, scroll restoration; admin-console pattern)

## 2. Integration pages

- [ ] 2.1 Write `plugins.md` (plugin lifecycle, `get_fetch_middlewares`/`get_rpc_middlewares` aggregation, script plugin, custom plugin recipe) + wrappers + manifest entries
- [ ] 2.2 Write `typed_api_deep_dive.md` (strictness/coercion tables, transfer modes incl. header vs body type-tag maps, `TypedJSONResponse` contrib usage)
- [ ] 2.3 Write `ui_headless_contract.md` (behavior-only guarantees, data-state vocabularies per component, class_name pass-through, import paths, themed-pair authoring recipe)
- [ ] 2.4 Write `persistence_patterns.md` (sync_tabs semantics, event coalescing, decision box: storage vs hydration vs URL state)

## 3. Revisions

- [ ] 3.1 Rework `custom_elements.md` to full interop coverage (wrapper boundaries, multiple roots, document-connection hooks, observed attributes, registration/hydration ordering) with links to Basic Components for naming basics
- [ ] 3.2 Resolve ③-2 back-link placeholders; add reciprocal links from all split-policy counterparts

## 4. Verification

- [ ] 4.1 Run the existing docs cross-link scan (main spec's rendered-site link rule) over the new pages; verify every Basic↔Advanced back-link pair resolves both ways
- [ ] 4.2 E2E for new pages (title, TOC, prod + static); sidebar group header visible
- [ ] 4.3 `ruff`/`pyright`/unit + `webcompy generate` + docs E2E + `check-doc-spec-refs.py` + `openspec validate feat-docs-advanced-integration`
