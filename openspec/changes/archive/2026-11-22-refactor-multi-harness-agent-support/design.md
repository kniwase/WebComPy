# Design: Multi-Harness Coding Agent Support

## Context

WebComPy previously restructured its OpenCode tooling so procedural knowledge lives in skills (`webcompy-*` and `openspec-*`) and agents (`webcompy-reviewer`, `webcompy-inspector`) act only as thin permission envelopes. However, all artifacts still live exclusively under `.opencode/`, `AGENTS.md` grew to ~42 KB by embedding full spec lookup tables, and contributor conventions assume OpenCode for local commits and workflows.

Antigravity (`agy` / IDE / App), Claude Code, OpenCode, Codex CLI, Cursor, and Gemini CLI share the Agent Skills standard and `AGENTS.md` ecosystem, but differ in discovery paths, per-file rule caps, slash-command invocation, and agent sandboxing:

- **Antigravity**: Reads `AGENTS.md` and `.agents/skills/*/SKILL.md` natively (where skills are also invocable as `/<skill-name>`), enforces a 24,000-byte per-file rule cap, and deprecated `.agent/workflows/`.
- **Claude Code**: Reads `CLAUDE.md` natively, scans `.claude/skills/` and `.claude/commands/` natively (requiring physical directories with individual entry symlinks rather than a symlinked parent directory), and supports `.claude/agents/*.md` subagent sandboxes.
- **OpenCode**: Reads `AGENTS.md`, `.agents/skills/`, `.opencode/commands/`, and `.opencode/agents/*.md` (used locally and by CI).

## Goals / Non-Goals

### Goals
- Maintain a single source of truth for all skills (`.agents/skills/`) and slash commands (`.agents/commands/`) without duplicating Markdown content.
- Keep `AGENTS.md` well under 24,000 bytes so Antigravity and all other harnesses ingest every rule (especially Git Conventions and Language Rules) without truncation.
- Support Claude Code cleanly via `CLAUDE.md`, physical mirror directories containing per-entry relative symlinks, and thin `.claude/agents/` envelopes.
- Keep `.github/workflows/ci.yml` working unchanged on OpenCode.
- Enforce spec-reference validity, `AGENTS.md` byte limits, and symlink parity mechanically in `scripts/check-doc-spec-refs.py`.

### Non-Goals
- Refactoring CI AI review off OpenCode.
- Supporting native Windows without symlink support (Unix and WSL2 are assumed).
- Creating deprecated `.agent/workflows/` files for Antigravity.
- Modifying runtime code under `packages/` or archived OpenSpec records.

## Decisions

### D1: `.agents/skills/` as skill SSOT
All 17 skills (7 `webcompy-*` + 10 `openspec-*`) move from `.opencode/skills/` to `.agents/skills/`. OpenCode, Antigravity, Codex CLI, Cursor, and Gemini CLI discover `.agents/skills/` natively with no extra adapter files.

*Alternatives considered:*
- *Build-time copy generator into `.opencode/`, `.claude/`, `.agents/`*: introduces duplicate committed files and generator maintenance overhead. Rejected.

### D2: `.agents/commands/` as `/opsx-*` slash command SSOT
All 8 `.opencode/commands/opsx-*.md` files move to `.agents/commands/` and are symlinked into both `.opencode/commands/` and `.claude/commands/`. Both harnesses share the exact `description:` frontmatter + `$ARGUMENTS` Markdown format. Antigravity deprecated `.agent/workflows/` in favor of Agent Skills under `.agents/skills/<name>/SKILL.md`, which are directly invocable as `/<skill-name>` (e.g., `/openspec-propose`, `/openspec-explore`), so no `.agent/workflows/` directory is created.

### D3: Physical mirror directories with individual relative symlinks
`.claude/skills/`, `.claude/commands/`, and `.opencode/commands/` MUST remain physical directories containing individual relative symlinks (`../../.agents/skills/<name>` and `../../.agents/commands/<file>`). Claude Code's discovery scanner skips a symlinked top-level `.claude/skills` directory. Although OpenCode scans both `.agents/skills/` and `.claude/skills/`, it deduplicates matching skill names safely.

### D4: Extract `openspec/SPEC_INDEX.md` and symlink `CLAUDE.md`
`Framework Invariants`, `File → Spec Mapping`, and `Current Specs` are extracted verbatim from `AGENTS.md` into `openspec/SPEC_INDEX.md`. `AGENTS.md` keeps core dual-environment rules, commands, conventions, git rules, skill summaries, and language rules alongside an explicit instruction to consult `openspec/SPEC_INDEX.md` before modifying or reviewing code. Root `CLAUDE.md` is a relative symlink pointing to `AGENTS.md` (`CLAUDE.md -> AGENTS.md`), keeping the ruleset identical across Claude Code and all `AGENTS.md`-reading harnesses without duplicating text or relying on `@`-import syntax.

### D5: Thin per-harness agent envelopes with CI unchanged
`.opencode/agents/webcompy-reviewer.md` and `.opencode/agents/webcompy-inspector.md` remain for OpenCode and `.github/workflows/ci.yml`, updating only their fallback skill read paths to `.agents/skills/`. Matching thin envelopes `.claude/agents/webcompy-reviewer.md` and `.claude/agents/webcompy-inspector.md` provide Claude Code read-only / inspect-only subagent boundaries.

### D6: Mechanical guardrails in `scripts/check-doc-spec-refs.py`
The existing CI-enforced guardrail script is extended to:
1. Scan `openspec/SPEC_INDEX.md` and `.agents/skills/*/SKILL.md` (replacing `.opencode/skills/`).
2. Fail if `AGENTS.md` exceeds 24,000 UTF-8 bytes.
3. Fail if `CLAUDE.md` is missing or not a valid relative symlink to `AGENTS.md`, or if `.claude/skills/`, `.claude/commands/`, or `.opencode/commands/` is missing, is itself a symlink, is out of 1-to-1 parity with `.agents/`, or contains broken/non-relative symlinks.

## Risks / Trade-offs

- [Symlinks on native Windows without Developer Mode] → Accepted; Unix/WSL2 is the target development environment.
- [Extra indirection from `AGENTS.md` to `openspec/SPEC_INDEX.md`] → Mitigated by explicit instructions in `AGENTS.md` and `webcompy-review/SKILL.md` plus preserving `AGENTS.md`'s 24 KB readability across all harnesses.
- [OpenCode scanning both `.agents/skills/` and `.claude/skills/`] → OpenCode deduplicates skills by name with only an informational log message; verified non-breaking.

## Migration Plan

1. Move skills and commands to `.agents/` and create individual relative symlinks in `.claude/skills/`, `.claude/commands/`, and `.opencode/commands/`.
2. Extract `openspec/SPEC_INDEX.md` from `AGENTS.md` and create `CLAUDE.md`.
3. Update skill/agent path references and add `.claude/agents/` envelopes.
4. Update `scripts/check-doc-spec-refs.py`, `openspec/config.yaml`, `CONTRIBUTING*.md`, and `.gitignore`.
5. Sync `doc-spec-references` spec, archive the OpenSpec change, and verify all CI checks pass locally.
