# Proposal: refactor-remove-github-pages-artifacts

## Why

Documentation hosting fully migrated from GitHub Pages to Cloudflare Pages, but the SSG pipeline still emits GitHub Pages-specific artifacts: a `CNAME` file driven by the public `WebComPyBuildConfig.cname` option, and an unconditionally written `.nojekyll` marker. These are dead weight on every build and the `cname` option is a public config API that no longer does anything useful. Removing them before the v0.1.0 release avoids shipping a no-op public API in the first semver-versioned release.

## What Changes

- **BREAKING**: Remove the `cname` field from `WebComPyBuildConfig` (`webcompy_cli.config`). There is no in-config replacement — custom domains are configured directly at the hosting provider (Cloudflare Pages), not in the build configuration.
- Remove the writing of the `CNAME` file from the SSG output in `generate_static_site` when `cname` is set (the entire code path goes away with the field).
- Remove the unconditional `.nojekyll` file creation from the SSG output. Cloudflare Pages does not use Jekyll and ignores the marker; GitHub Pages is no longer a supported deployment target for this repository's own docs pipeline.
- Drop `cname="webcompy.net"` from `docs_app/webcompy_config.py`.
- Update the unit assertion on `WebComPyBuildConfig` defaults (`tests/test_config_dataclasses.py`) accordingly.
- Update the `app-lifecycle`, `config-separation`, and `app-config` specs to drop `CNAME`/`.nojekyll`/`cname` behavior (details in delta specs).

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `app-lifecycle`: The "The SSG entry point shall be a module-level function" requirement no longer includes `.nojekyll` creation; the "Generating with custom config" scenario (which asserts `CNAME` output via the retired `GenerateConfig` API) is rewritten to assert custom-`dist` output only.
- `config-separation`: The `WebComPyBuildConfig` defaults scenario drops the `cname=""` entry.
- `app-config`: The `WebComPyBuildConfig` defaults scenario drops the `cname=""` entry.

## Impact

- Affected code: `packages/webcompy-cli/src/webcompy_cli/_generate.py` (CNAME + `.nojekyll` writing), `packages/webcompy-cli/src/webcompy_cli/config/_build_config.py` (field + docstrings), `docs_app/webcompy_config.py`, `tests/test_config_dataclasses.py`.
- Affected specs: `openspec/specs/app-lifecycle/spec.md`, `openspec/specs/config-separation/spec.md`, `openspec/specs/app-config/spec.md`.
- SSG output: generated `dist/` no longer contains `CNAME` or `.nojekyll`; all other emitted files are unchanged.
- Downstream users: only projects that passed `cname=` to `WebComPyBuildConfig`; the field is removed outright (pre-1.0, clean break). No browser-runtime, server, or CLI-surface impact beyond the SSG file emission.

## Non-goals

- No replacement configuration for deployment domains: domain management stays a hosting-provider concern (Cloudflare Pages custom domains), not a framework config.
- No changes to other `WebComPyBuildConfig` fields or to the `dist`/`static_files_dir` output behavior.
- No remediation of pre-existing spec drift discovered during scoping (for example, legacy `### MODIFIED:` header text left in the `config-separation`/`app-config` main specs, and stale `assets=None` / missing `resource_transfer` / `pwa` entries in the same defaults scenario). Fixing those is tracked separately; only the `cname`-related wording is touched here.
