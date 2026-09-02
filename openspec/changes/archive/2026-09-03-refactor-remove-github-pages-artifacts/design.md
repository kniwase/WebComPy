# Design: refactor-remove-github-pages-artifacts

## Context

See proposal.md for motivation. The relevant current state:

- `WebComPyBuildConfig` (`packages/webcompy-cli/src/webcompy_cli/config/_build_config.py`) declares a `cname: str = ""` field, documented in its Attributes/Args docstrings.
- `generate_static_site()` (`packages/webcompy-cli/src/webcompy_cli/_generate.py`) touches `.nojekyll` unconditionally and writes a `CNAME` file when `build_config.cname` is set.
- The specs in `openspec/specs/` still norm these behaviors: `app-lifecycle` ("The SSG entry point shall be a module-level function"), `config-separation` and `app-config` (the `WebComPyBuildConfig` defaults scenario).
- Repo docs hosting runs entirely on Cloudflare Pages; no consumer in this repository (tests, e2e, scripts, `template_data/`) references `cname`, `CNAME`, or `.nojekyll` besides the locations above.

## Goals / Non-Goals

**Goals:**
- Delete the `cname` public config surface and the two GitHub Pages file emissions in one pass, with specs and tests updated in the same change.
- Keep every other SSG output byte-identical (same file set minus `CNAME`/`.nojekyll`).

**Non-Goals:**
- No replacement knob for deployment domains (hosting-provider concern).
- No general repair of pre-existing spec drift in `config-separation`/`app-config` beyond what this change's delta requires (see Decisions).

## Decisions

### Remove the field outright instead of deprecating
Alternative: keep `cname` as an ignored/deprecated field for one release. Rejected: the project is pre-1.0 with a deliberate clean break before v0.1.0, a deprecated no-op field would linger in the public dataclass docstrings and type surface, and there is exactly one in-repo consumer (`docs_app`) that we control.

### Drop `.nojekyll` together with `cname`, unconditionally
`​.nojekyll` only matters to GitHub Pages; Cloudflare Pages ignores dotfiles it doesn't know. Alternative: gate it behind config like `cname` was. Rejected: a config option that exists solely to disable a marker file for a hosting provider we no longer use is not worth keeping. Risk: a downstream user who deploys to GitHub Pages manually loses a convenience, not a capability — they can add the file themselves (documented in the changelog entry of the release).

### Rewrite the "Generating with custom config" scenario rather than delete it
The validator requires a MODIFIED block to carry every scenario the current requirement has, so dropping the scenario silently is not an option. Its invocation form (`generate_config=GenerateConfig(...)`) references an API already retired by the config-separation change — the scenario is stale precisely because it is the last surface of the `CNAME`-carrying parameter, so the same change that removes `cname` modernizes it: the scenario is rewritten to drive output location through `WebComPyBuildConfig.dist` (resolved relative to the app package path) and to drop the `CNAME` assertion. The requirement description sentence is likewise rephrased to the actual signature (`generate_static_site(app)` with the app discovered from configuration when omitted). Other stale wording in unrelated requirements (e.g. `assets=None` in the config specs' defaults list) is left untouched per the proposal's Non-goals.

### Normalize the touched requirement headers during sync
The `WebComPyBuildConfig` requirement blocks in `openspec/specs/config-separation/spec.md` and `openspec/specs/app-config/spec.md` carry a legacy `### MODIFIED: ` header prefix left over from an older archive sync, which prevents name-matching the delta's canonical `### Requirement: ` header. The sync step renames exactly those two headers (content unchanged) so the MODIFIED delta replaces the block instead of appending a duplicate. All other malformed headers in those files are left as-is.

Revision (discovered during sync): renaming only those two headers is not sufficient. The parser treats only canonical `### Requirement:` headers as block boundaries, so each remaining malformed header keeps concatenating its scenarios into the preceding canonical block — once the `WebComPyBuildConfig` requirement becomes name-matchable, it appears to own every scenario down to the next canonical header (dozens in both files), and change validation rejects the MODIFIED delta for "omitting" scenarios that actually belong to other requirements, blocking archive. The sync therefore normalizes ALL legacy `### MODIFIED:` / `### ADDED:` headers in these two files to `### Requirement:` (header line only; block content and requirement names unchanged, no name collisions). Other spec files with malformed headers remain out of scope.

## Risks / Trade-offs

- [Downstream projects pass `cname=` to `WebComPyBuildConfig`] → TypeError at config construction; acceptable pre-1.0, called out as BREAKING in the proposal and in the eventual v0.1.0 changelog.
- [Spec sync tooling silently duplicates the requirement instead of replacing it if the header rename is missed] → Verification task: after sync, `grep` the main specs for `cname` and `### MODIFIED: WebComPyBuildConfig` and confirm zero matches; `openspec validate --specs` must pass.
- [A future GitHub Pages deployment of the docs silently breaks] → Out of scope by decision (Cloudflare Pages is the supported target); note retained in proposal Non-goals.

## Migration Plan

Single PR: remove field + emissions + config usage + test assertion, sync specs, archive the change. No data or runtime migration; rollback is a revert of the commit. Downstream migration (for external users, if any): delete the `cname` kwarg from their `webcompy_config.py`.
