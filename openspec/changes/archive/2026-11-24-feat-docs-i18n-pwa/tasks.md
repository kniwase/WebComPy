# Tasks: feat-docs-i18n-pwa

## 1. i18n rework

- [x] 1.1 Rewrite `docs_app/documents/i18n.md` to the Advanced structure with catalog/plurals/fallback/setup/recipes sections
- [x] 1.2 Add the deterministic-parity walkthrough (diagram) and the late-mutation pitfall recipe; assign group `Architecture & Integration`

## 2. PWA rework

- [x] 2.1 Rewrite `docs_app/documents/pwa.md`: generated artifacts (manifest, SW template, injection) vs runtime behavior (activation, cleanup, offline fallback) halves
- [x] 2.2 Add caching decision table with config snippets, dev-mode-off note, base-URL scoping, and an install/update observation recipe; assign group `Rendering & Performance`

## 3. Verification

- [x] 3.1 Update page E2E heading/TOC expectations; link-check test pass; `ruff`/`pyright`/unit + `webcompy generate` + docs E2E + `openspec validate feat-docs-i18n-pwa`
