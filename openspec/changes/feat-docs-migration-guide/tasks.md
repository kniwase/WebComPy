# Tasks: feat-docs-migration-guide

## 1. Demo app

- [ ] 1.1 Build the before/after demo: WebComPy user-list search app (`static/_demos/migration_users/`) with `FetchMiddleware` mock for `/api/users`, live-filter on input; register in `standard.html`
- [ ] 1.2 Author the Jinja2 side source (base.html, users.html, FastAPI route) for the comparison column

## 2. Pages

- [ ] 2.1 Write `migration_from_jinja2_fastapi.md`: architecture-shift table, strategy decision section, conversion table (directive rows with links), per-concern mapping sections, phase checklist with exit criteria, honest scope note (non-browser HTML stays server-side); wrapper + manifest `Migration` category (inserted before the existing `Examples` category per the standalone ordering)
- [ ] 2.2 Write `migration_compatibility_notes.md`: construct matrix incl. supported-identically, renamed (filters), replaced (extends/block/include), rejected (`set`/`with`/`macro`/tests/`{% for %}…{% else %}`) with exact error strings; wrapper + manifest
- [ ] 2.3 Add Home feature-band card "Coming from Jinja2 + FastAPI?" linking to the guide (plain task; no spec change)

## 3. Verification

- [ ] 3.1 E2E for both pages (title, TOC, demo renders in static mode; prod + static)
- [ ] 3.2 Link-check pass over all guide links; `ruff`/`pyright`/unit + `webcompy generate` + docs E2E + `check-doc-spec-refs.py` + `openspec validate feat-docs-migration-guide`
