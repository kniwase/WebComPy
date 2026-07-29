---
name: webcompy-server-development
description: Develop WebComPy server-side code (CLI tools, dev server, SSG, server ports). Use when modifying packages/webcompy-server and packages/webcompy-cli.
---

You are working on server-side WebComPy code (CLI tools, Starlette dev server, static site generator). This code runs in standard Python with uvicorn, aiofiles, etc.

## Core Responsibilities

- CLI entry points, argument parsing, and server lifecycle
- Browser inspection subcommands (`packages/webcompy-cli/src/webcompy_cli/_inspect.py`)
- Dev server (Starlette + uvicorn with hot-reload)
- Static site generation (HTML/wheel generation for deployment)
- Application bootstrapping and server entry points
- Server-side port implementations (`packages/webcompy-server/src/webcompy_server/ports/`) — fake DOM, virtual DOM for SSG and testing

## Key Constraints

- Server-only imports: uvicorn, starlette, aiofiles must NOT be imported in browser code paths
- `discover_config()` for configuration resolution
- `packages/webcompy-server/src/webcompy_server/` and `packages/webcompy-cli/src/webcompy_cli/` are server-only package roots

## Runtime Context Detection

Code under `packages/webcompy-server/` and `packages/webcompy-cli/` runs only in CPython. Imports of `uvicorn`, `starlette`, `aiofiles` indicate server-only code paths and MUST NOT appear in `packages/webcompy/` modules intended for the browser. The `webcompy.app` module is shared between both runtime contexts; check for `platform.system() == "Emscripten"` guards before assuming browser vs server availability of any symbol.

## OpenSpec References

Before modifying server-side code, read the relevant specs to ensure compliance:

- `openspec/specs/cli/spec.md` — Dev server, SSG, project scaffolding
- `openspec/specs/project-config/spec.md` — Two-file project configuration
- `openspec/specs/config-separation/spec.md` — Browser vs server config separation
- `openspec/specs/inspect-cli/spec.md` — Browser inspection CLI commands
- `openspec/specs/app-config/spec.md` — AppConfig, ServerConfig, GenerateConfig

## Patterns

- Use `discover_config()` for configuration resolution
- Server-only ports (`packages/webcompy-server/src/webcompy_server/ports/`) implement the same ABCs browser ports do
- CLI subcommands live in `packages/webcompy-cli/src/webcompy_cli/_<subcommand>.py`

## Related Skills

- `webcompy-browser-development` — browser-side runtime shares dual-environment code in `webcompy.app`
- `webcompy-docs-development` — documentation site generation uses server CLI commands
- `webcompy-local-ci` — running CI checks locally before pushing
- `webcompy-review` — spec-driven code review for PRs
