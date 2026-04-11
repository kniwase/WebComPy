# WebComPy — Python Frontend Framework

## Overview

WebComPy is a Python frontend framework that runs in the browser via PyScript.
It enables building single-page web applications entirely in Python.

## Dual-Environment Architecture (CRITICAL)

This framework operates in two distinct runtime contexts:

- **Browser (PyScript/Emscripten)**: Reactive system, component rendering, DOM manipulation, routing
- **Server (Standard Python)**: CLI tools, dev server (Starlette+uvicorn), static site generator

When modifying code, always consider which context the code runs in.
`platform.system() == "Emscripten"` is used to detect the browser environment.
Code in `webcompy/cli/` and `webcompy/_browser/` is context-sensitive.

## Project Structure

- `webcompy/` — Main package source
  - `components/` — Component system (base classes, decorators, generators)
  - `elements/` — Virtual DOM / HTML element system
  - `reactive/` — Reactive state management (Reactive, Computed, ReactiveList, ReactiveDict)
  - `router/` — Client-side routing (history/hash modes)
  - `app/` — Core application class
  - `cli/` — CLI tools (start, generate, init)
  - `ajax/` — HTTP client (browser fetch)
  - `aio/` — Async utilities (AsyncComputed, AsyncWrapper)
  - `_browser/` — Browser API abstraction layer
- `docs_src/` — Documentation site source
- `docs/` — Generated static site (GitHub Pages output, DO NOT Edit directly)

## Build & Run Commands

- Install dependencies: `uv sync`
- Dev server: `uv run python -m webcompy start --dev`
- Static site generation: `uv run python -m webcompy generate`
- Project scaffolding: `uv run python -m webcompy init`
- Build package: `uv build`

## Lint & Type Check Commands

- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Type check: `uv run pyright`
- Pre-commit hooks run ruff (lint + format) and pyright automatically on commit

## Code Conventions

- Python 3.12+ (aligned with latest PyScript/Pyodide runtime)
- Package management with `uv` — use `uv add <package>` to add dependencies, `uv lock` to update lockfile
- Type annotations throughout (package includes `py.typed` marker and `.pyi` stubs)
- No comments in code unless explicitly requested
- Component classes use decorators: `@component_template`, `@on_before_rendering`
- Reactive values are defined via `Reactive`, `Computed`, `ReactiveList`, `ReactiveDict`

## Important Notes

- Do NOT edit files in `docs/` — they are generated output
- The `.pyi` stub file at `webcompy/_browser/_modules.pyi` provides type hints for browser APIs
- `webcompy/cli/template_data/` contains the project template for `webcompy init`

## Git Conventions

### Commit Messages

Commit messages MUST use the following format:

```
<type>: <description>

🤖 Generated with opencode

Co-Authored-By: opencode <noreply@opencode.ai>
```

Where `<type>` is one of:

- `feat:` — New feature
- `fix:` — Bug fix
- `refactor:` — Code refactoring without behavior change
- `docs:` — Documentation changes
- `chore:` — Maintenance tasks, dependency updates, etc.
- `test:` — Adding or updating tests
- `style:` — Code style changes (formatting, etc.)
- `perf:` — Performance improvements

The footer with `Co-Authored-By` MUST be included on every commit.

### Branch Names

Branch names MUST use the following prefix format:

```
<type>/<description>
```

Where `<type>` is one of:

- `feat/` — New feature (e.g., `feat/add-di-system`)
- `fix/` — Bug fix (e.g., `fix/reactive-update-order`)
- `refactor/` — Code refactoring (e.g., `refactor/component-lifecycle`)
- `docs/` — Documentation (e.g., `docs/api-reference`)
- `chore/` — Maintenance (e.g., `chore/update-dependencies`)
- `test/` — Testing (e.g., `test/reactive-list`)
- `perf/` — Performance (e.g., `perf/dom-patching`)

Use kebab-case for the description part of branch names.