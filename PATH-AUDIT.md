# Path Audit — 4-Package Workspace Split (#182)

**Date:** 2026-07-02
**Branch:** `feat/async-ssr-pipeline-rollout`
**Context:** Commit `8a1b29d refactor: split WebComPy into 4 packages under uv workspace (#182)` moved
all framework code from a single `webcompy/` monorepo into four workspace packages. The seven
in-progress OpenSpec change proposals (`openspec/changes/feat-*`, `openspec/changes/fix-*`) and
several main `openspec/specs/*` documents were written before the split and still reference the
old paths. This document catalogs every old path that needs to be updated.

## Package Layout (Post #182)

| Package | Old root | New path |
|---------|----------|----------|
| `webcompy` (core) | `webcompy/` | `packages/webcompy/src/webcompy/` |
| `webcompy_server` | `webcompy/ports/_server/`, `webcompy_server/` (server-specific) | `packages/webcompy-server/src/webcompy_server/` |
| `webcompy_cli` | `webcompy/cli/` | `packages/webcompy-cli/src/webcompy_cli/` |
| `webcompy_testing` | `webcompy/testing/` | `packages/webcompy-testing/src/webcompy_testing/` |

## Full Path Mapping

### Core package (`packages/webcompy/src/webcompy/`)

| Old path | New path |
|----------|----------|
| `webcompy/aio/__init__.py` | `packages/webcompy/src/webcompy/aio/__init__.py` |
| `webcompy/aio/_async_result.py` | `packages/webcompy/src/webcompy/aio/_async_result.py` |
| `webcompy/app/_app.py` | `packages/webcompy/src/webcompy/app/_app.py` |
| `webcompy/app/_config.py` | `packages/webcompy/src/webcompy/app/_config.py` |
| `webcompy/app/_root_component.py` | `packages/webcompy/src/webcompy/app/_root_component.py` |
| `webcompy/components/_component.py` | `packages/webcompy/src/webcompy/components/_component.py` |
| `webcompy/components/_generator.py` | `packages/webcompy/src/webcompy/components/_generator.py` |
| `webcompy/components/_libs.py` | `packages/webcompy/src/webcompy/components/_libs.py` |
| `webcompy/di/__init__.py` | `packages/webcompy/src/webcompy/di/__init__.py` |
| `webcompy/di/_keys.py` | `packages/webcompy/src/webcompy/di/_keys.py` |
| `webcompy/elements/__init__.py` | `packages/webcompy/src/webcompy/elements/__init__.py` |
| `webcompy/elements/_dom_objs.py` | `packages/webcompy/src/webcompy/elements/_dom_objs.py` |
| `webcompy/elements/generators.py` | `packages/webcompy/src/webcompy/elements/generators.py` |
| `webcompy/elements/types/_abstract.py` | `packages/webcompy/src/webcompy/elements/types/_abstract.py` |
| `webcompy/elements/types/_base.py` | `packages/webcompy/src/webcompy/elements/types/_base.py` |
| `webcompy/elements/types/_client_only.py` *(new)* | `packages/webcompy/src/webcompy/elements/types/_client_only.py` |
| `webcompy/elements/types/_dynamic.py` | `packages/webcompy/src/webcompy/elements/types/_dynamic.py` |
| `webcompy/elements/types/_repeat.py` | `packages/webcompy/src/webcompy/elements/types/_repeat.py` |
| `webcompy/elements/types/_suspense.py` *(new)* | `packages/webcompy/src/webcompy/elements/types/_suspense.py` |
| `webcompy/elements/types/_switch.py` | `packages/webcompy/src/webcompy/elements/types/_switch.py` |
| `webcompy/elements/types/__init__.py` | `packages/webcompy/src/webcompy/elements/types/__init__.py` |
| `webcompy/hydration/__init__.py` *(new)* | `packages/webcompy/src/webcompy/hydration/__init__.py` |
| `webcompy/hydration/_collect.py` *(new)* | `packages/webcompy/src/webcompy/hydration/_collect.py` |
| `webcompy/hydration/_payload.py` *(new)* | `packages/webcompy/src/webcompy/hydration/_payload.py` |
| `webcompy/ports/_browser/_fetch.py` | `packages/webcompy/src/webcompy/ports/_browser/_fetch.py` |
| `webcompy/ports/_browser/_raw.pyi` | `packages/webcompy/src/webcompy/ports/_browser/_raw.pyi` |
| `webcompy/ports/_dom.py` | `packages/webcompy/src/webcompy/ports/_dom.py` |
| `webcompy/ports/_fetch.py` | `packages/webcompy/src/webcompy/ports/_fetch.py` |
| `webcompy/ports/_keys.py` | `packages/webcompy/src/webcompy/ports/_keys.py` |
| `webcompy/signal/_base.py` | `packages/webcompy/src/webcompy/signal/_base.py` |
| `webcompy/ui/code_block/lexers/_adapters/_pygments.py` | `packages/webcompy/src/webcompy/ui/code_block/lexers/_adapters/_pygments.py` |

### Server package (`packages/webcompy-server/src/webcompy_server/`)

| Old path | New path |
|----------|----------|
| `webcompy/ports/_server/_fetch.py` | `packages/webcompy-server/src/webcompy_server/ports/_fetch.py` |
| `webcompy/ports/_server/_virtual_dom.py` | `packages/webcompy-server/src/webcompy_server/ports/_virtual_dom.py` |
| `webcompy/cli/_html.py` | `packages/webcompy-server/src/webcompy_server/_html.py` |

### CLI package (`packages/webcompy-cli/src/webcompy_cli/`)

| Old path | New path |
|----------|----------|
| `webcompy/cli/__main__.py` | `packages/webcompy-cli/src/webcompy_cli/__main__.py` |
| `webcompy/cli/_build.py` *(new)* | `packages/webcompy-cli/src/webcompy_cli/_build.py` |
| `webcompy/cli/_generate.py` | `packages/webcompy-cli/src/webcompy_cli/_generate.py` |
| `webcompy/cli/_server.py` | `packages/webcompy-cli/src/webcompy_cli/_server.py` |
| `webcompy/cli/_wheel_builder.py` | `packages/webcompy-cli/src/webcompy_cli/_wheel_builder.py` |

### Testing package (`packages/webcompy-testing/src/webcompy_testing/`)

| Old path | New path |
|----------|----------|
| `webcompy/testing/_asgi.py` | `packages/webcompy-testing/src/webcompy_testing/_asgi.py` |
| `webcompy/testing/__init__.py` | `packages/webcompy-testing/src/webcompy_testing/__init__.py` |

## In-Progress Change Proposals (tasks.md / design.md / proposal.md)

All seven changes under `openspec/changes/` reference old paths in their `tasks.md` and `design.md`.
Updates will be applied per-change in subsequent commits.

| Change | Files referencing old paths | Status |
|--------|------------------------------|--------|
| `fix-ssr-hydration-skip` | `tasks.md` (1 path: `webcompy/app/_app.py`) | Phase 1-2 |
| `feat-server-fetch-port-asgi` | `tasks.md`, `design.md` (server fetch port, ASGI app) | Phase 1-3 |
| `feat-async-component-setup` | `tasks.md`, `design.md` (components + aio) | Phase 1-4 |
| `feat-client-only-component` | `tasks.md`, `design.md` (elements + root_component) | Phase 1-5 |
| `feat-ssg-via-ssr` | `tasks.md`, `design.md` (cli + html) | Phase 1-6 |
| `feat-suspense-component` | `tasks.md`, `design.md` (elements + components) | Phase 1-7 (to be merged in Phase 2) |
| `feat-hydration-data-transfer` | `tasks.md`, `design.md` (aio + ports + app) | Phase 1-8 (to be merged in Phase 2) |

## Main Spec Files With Old Paths

| File | Lines with old paths | Action |
|------|----------------------|--------|
| `openspec/specs/architecture/spec.md` | 35 (`webcompy/ports/_browser/_raw.py`) | Update |
| `openspec/specs/async-rendering/spec.md` | 233, 332 (`webcompy/signal/_base.py`, `webcompy/aio/_aio.py`) | Update |
| `openspec/specs/code-block/spec.md` | 133 (`webcompy/ui/code_block/lexers/_adapters/_pygments.py`) | Verify & update |
| `openspec/specs/plugin-script/spec.md` | 83 (`webcompy/app/_config.py`) | Update |
| `openspec/specs/port-abstraction/spec.md` | 145 (`webcompy/elements/_dom_objs.py`, `webcompy/ports/_dom.py`) | Update |
| `openspec/specs/port-provisioning/spec.md` | 25 (`webcompy/ports/_keys.py`) | Update |
| `openspec/specs/testing-module/spec.md` | 213 (`webcompy/testing/`, `webcompy/cli/_wheel_builder.py`) | Update |
| `openspec/specs/theme-system/spec.md` | 50 (`webcompy/cli/_server.py`) | Update |
| `openspec/specs/virtual-dom/spec.md` | 9, 75, 173 (already partially updated) | Update |
| `openspec/specs/wheel-builder/spec.md` | 7, 12 (already partially updated) | Update |
| `openspec/specs/cli/spec.md` | 37, 43, 46, 47, 56, 58, 63, 64, 203 (config file paths, not package paths — these are user-facing config files, NOT framework paths; **no update needed**) | Skip |
| `openspec/specs/project-config/spec.md` | various (config file paths, not package paths) | Skip |
| `openspec/specs/lockfile/spec.md` | 10, 125, 126, 129, 154, 162, 263, 270 (config file paths) | Skip |
| `openspec/specs/app-lifecycle/spec.md` | 108, 110, 111, 116, 117, 136, 137 (config file paths) | Skip |

> **Note:** `webcompy_config.py` and `webcompy_server_config.py` are user-facing configuration file
> names, NOT Python import paths. They were renamed in earlier changes and the spec text correctly
> reflects the final state. These references must NOT be changed.

## CI Workflow (`.github/workflows/ci.yml`)

The CI workflow is **already up-to-date** with the post-split package layout:

- Path filters: `packages/`, `docs_app/`, `tests/`, `scripts/`, `pyproject.toml`, `uv.lock`
- Coverage packages: `webcompy`, `webcompy_server`, `webcompy_cli`, `webcompy_testing`
- E2E test paths: `tests/e2e/`, `tests/e2e_docs/`, `docs_app/dist/`

**No changes required** for `.github/workflows/ci.yml` itself.

## Implementation Plan

1. **Phase 1-2 to 1-8:** Update each change's `tasks.md` and `design.md` to use new paths (one
   commit per change).
2. **Phase 1-9:** Update main spec files (consolidated commit since CI workflow is already correct).
3. **Phase 2:** Merge `feat-suspense-component` + `feat-hydration-data-transfer` into
   `feat-suspense-and-hydration-data-transfer`, reusing the path-corrected files.
4. **Phase 3:** Sync `fix-ssr-hydration-skip` delta spec to main specs, then archive.
5. **Phase 4:** Risk assessment.
6. **Phase 5:** Implement the remaining changes.
