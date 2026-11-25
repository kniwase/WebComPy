# Proposal: feat-docs-api-reference

## Why

Every other category teaches concepts; none answers "what exactly are this function's parameters?" Docstring coverage is now complete and CI-strict (api-docstrings), so a reference layer can be authored cheaply and kept honest — the docstrings are the machine-checked source of truth. Vue-style hand-written module pages (decision B from planning) give curated grouping and prose while the checker guarantees signature accuracy.

## What Changes

- Add a skeleton generator `scripts/generate_api_reference.py`: reuses the public-API resolution of `scripts/check-docstrings.py` (re-export chains from `__init__.py` into private modules, class members, PEP 224 constants) to emit, per module page, the heading structure + signature + first docstring line; authors then hand-write grouping prose, usage notes, and cross-links. Output is committed generated Markdown under `docs_app/documents/api/`.
- Add the `API Reference` standalone category (`/documents/api/`) with pages per module group: `webcompy` (app/config, components, elements, signal, template, router, di, ajax-aio, forms, storage, events), `webcompy.ui` (theme, code block, components, styles), `webcompy.rpc` + `webcompy_server.rpc`, `webcompy.hydration` + resources/ports, `webcompy_cli` + `webcompy_server`, `webcompy_testing`.
- A regeneration discipline: a CI job runs the generator in `--check` mode and fails when committed reference pages drift from the current public API surface; adding public API therefore forces a reference refresh in the same PR (parallel to the docstring same-PR rule).
- Every Basic/Advanced page gains "Full API: /documents/api/<module>" links on its tables.

## Capabilities

### New Capabilities

- `docs-api-reference`: Reference generation, drift checking, page set, and the docstring-is-truth relationship.

### Modified Capabilities

- `docs-site-documents`: API Reference standalone category registration.

## Impact

- New `scripts/generate_api_reference.py` (+ `--check` mode) and CI step in the openspec/lint job
- `docs_app/documents/api/*.md` (generated base + hand prose), manifest category, wrappers, E2E page tests
- No runtime package changes; `api-docstrings` spec untouched (the checker remains the shared resolution source; the generator imports/parodies its logic)

## Known Issues Addressed

Turns the docstring-coverage initiative's finished surface into a consumer-facing reference.

## Non-goals

- Fully automatic prose generation (skeleton only; prose is authored)
- Type-hover documentation tools integration
- Reference pages for private internals beyond the checker's important-internals allowlist
