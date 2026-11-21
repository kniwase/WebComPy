## Why

WebComPy's AI agent tooling currently targets OpenCode exclusively: all skills live under `.opencode/skills/`, slash commands under `.opencode/commands/`, agent definitions under `.opencode/agents/`, and documentation/commit conventions assume OpenCode. In addition, `AGENTS.md` has grown to ~42 KB because it embeds the full `Framework Invariants`, `File → Spec Mapping`, and `Current Specs` tables inline. Because Antigravity enforces a 24,000-byte per-file rule cap, the trailing ~18 KB of `AGENTS.md` (including Git Conventions, Review Knowledge Maintenance, and Language Rules) is silently truncated. Meanwhile, Claude Code prioritizes `CLAUDE.md` and requires physical `.claude/skills/` and `.claude/commands/` directories with per-entry relative symlinks.

This change establishes a single-source-of-truth (SSOT) layout under `.agents/` and slims `AGENTS.md` so Antigravity, Claude Code, OpenCode, and other Agent Skills-compatible harnesses share identical project rules, skills, and slash commands without duplication.

## What Changes

- Move all 17 skills (`webcompy-*` and `openspec-*`) from `.opencode/skills/` to `.agents/skills/` as the single source of truth.
- Move all 8 `/opsx-*` slash commands from `.opencode/commands/` to `.agents/commands/` as the single source of truth, and expose them via individual relative symlinks in physical `.opencode/commands/` and `.claude/commands/` directories.
- Expose `.agents/skills/` to Claude Code via individual relative symlinks inside a physical `.claude/skills/` directory.
- Extract `Framework Invariants`, `File → Spec Mapping`, and `Current Specs` from `AGENTS.md` into `openspec/SPEC_INDEX.md`, keeping `AGENTS.md` well under 24,000 bytes with explicit pointers to `openspec/SPEC_INDEX.md`.
- Add root `CLAUDE.md` importing `@AGENTS.md`.
- Add thin Claude Code agent envelopes `.claude/agents/webcompy-reviewer.md` and `.claude/agents/webcompy-inspector.md`, and update `.opencode/agents/*.md` skill fallback paths to `.agents/skills/`.
- Update `webcompy-review` and `webcompy-local-ci` skill references to point to `openspec/SPEC_INDEX.md` and `.agents/` paths.
- Extend `scripts/check-doc-spec-refs.py` to scan `.agents/skills/*/SKILL.md` and `openspec/SPEC_INDEX.md`, enforce `AGENTS.md <= 24,000` bytes, and validate 1-to-1 symlink mirror parity across `.claude/skills/`, `.claude/commands/`, and `.opencode/commands/`.
- Make `AGENTS.md`, `CONTRIBUTING.md`, `CONTRIBUTING.ja.md`, `openspec/config.yaml`, and `.gitignore` harness-neutral while preserving OpenCode CI review behavior.
- Update the `doc-spec-references` specification to reflect the new universal doc paths, `AGENTS.md` byte limit, and symlink mirror parity checks.

## Known Issues Addressed

- No runtime known issues in `openspec/config.yaml` apply to this change (agent tooling and documentation only).
- Addresses the cross-harness compatibility issue where `AGENTS.md` (~42 KB) silently exceeds Antigravity's 24,000-byte per-file rule cap, truncating `Git Conventions` and `Language Rules`.

## Non-goals

- Changing the GitHub Actions AI review job in `.github/workflows/ci.yml` (CI continues to run on OpenCode via `webcompy-reviewer`).
- Windows native symlink compatibility (Unix/WSL2 development environments are assumed).
- Creating legacy `.agent/workflows/` files for Antigravity (deprecated in favor of Agent Skills under `.agents/skills/`).
- Modifying runtime framework code under `packages/` or historical archived changes under `openspec/changes/archive/`.

## Capabilities

### Modified Capabilities
- `doc-spec-references`: Update universal documentation file paths to `.agents/skills/*/SKILL.md` and `openspec/SPEC_INDEX.md`, add `AGENTS.md` 24,000-byte size cap enforcement, and add SSOT symlink mirror parity verification.

## Impact

- `AGENTS.md`, `CLAUDE.md`, `openspec/SPEC_INDEX.md` — concise cross-harness project rules, Claude entrypoint, and extracted spec navigation index.
- `.agents/skills/*`, `.agents/commands/*` — SSOT for all 17 skills and 8 slash commands.
- `.claude/skills/*`, `.claude/commands/*`, `.claude/agents/*` — Claude Code skill/command symlink mirrors and thin permission-sandboxed agent envelopes.
- `.opencode/agents/*`, `.opencode/commands/*` — OpenCode agent fallback paths updated and slash commands mirrored from `.agents/commands/`.
- `scripts/check-doc-spec-refs.py`, `openspec/config.yaml`, `openspec/specs/doc-spec-references/spec.md` — updated spec-governance rules and CI guardrail checks.
- `CONTRIBUTING.md`, `CONTRIBUTING.ja.md`, `.gitignore` — multi-harness documentation and local config ignores.
- No runtime code under `packages/` and no CI workflow files under `.github/workflows/` are altered.
