# Design: feat-docs-server-tooling

## Context

The CLI exposes `python -m webcompy {start,generate,init,lock,inspect}` (no console script entry point yet). Config is split per `config-separation` (`pyproject.toml` browser deps + `webcompy_config.py` build/server). ASGI story spans three specs: asgi-embed, asgi-mount capability within cli, server-fetch-asgi. Testing utilities live in `webcompy_testing`. The ③-0 category model enumerated four categories; this change adds a fifth (`Server & Tooling`) as an approved extension of that model (docs updated via spec delta).

## Decisions

1. **Fifth category, not an Advanced group.** Server material is a distinct reader journey (ops/build), and the category model was written as "three content categories + standalone sections"; Server & Tooling behaves like the standalone sections with its own URL prefix `/documents/server/`. **Rejected**: nesting under Advanced Usage — mixes application logic docs with toolchain docs and lengthens that category unfairly.
2. **cli-reference is generated-ish, not exhaustive prose**: one table of subcommands + flags cross-checked against the argparser at authoring time (a unit test asserts each documented subcommand/flag string appears in the parser), then worked examples only for the common flows. This keeps the page small and drift-checked.
3. **asgi-integration carries the migration pattern forward**: the host-mount snippet here is the canonical one reused by ③-10's migration guide (link, don't duplicate).
4. **serving-modes page answers "can I run this offline/behind a firewall"** (CDN vs local, pyscript bundle, `.webcompy_modules/` cache) — a real evaluation question; wheel modes table bundled vs split.
5. **testing page** documents tiers for app authors (unit w/ TestRenderer, browser tier notes, E2E w/ Playwright) and the fake-port inventory, ending with a "test a component that fetches" recipe.
6. Docs index (DOCS_INDEX page component) gains a fifth card; card list generated from manifest categories where feasible (small refactor noted in tasks).

## Risks

- [Flag drift between CLI argparser and docs] → the parser-vs-docs unit test (§2) is the mitigation.
- [Category model churn (four→five)] → intentional and spec'd; later changes (Examples/API) already planned standalone categories, so the model states "content categories + tool/standalone categories with fixed prefixes".

## Migration Plan

Additive; merge after ③-0/③-5 (back-link targets exist).

## Open Questions

None.
