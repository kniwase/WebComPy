# Tasks: Multi-Harness Coding Agent Support

- [x] 1. Move skills and slash commands to `.agents/` SSOT and create harness symlinks (`.claude/skills/`, `.claude/commands/`, `.opencode/commands/`)
- [x] 2. Split `AGENTS.md` into concise rules (<= 24,000 bytes) plus `openspec/SPEC_INDEX.md` and add root `CLAUDE.md` symlink to `AGENTS.md`
- [x] 3. Update skill/agent references to `.agents/` and `openspec/SPEC_INDEX.md`, and add Claude Code thin agent envelopes under `.claude/agents/`
- [x] 4. Update `scripts/check-doc-spec-refs.py`, `openspec/config.yaml`, `CONTRIBUTING.md`, `CONTRIBUTING.ja.md`, and `.gitignore`
- [x] 5. Validate all checks, sync `doc-spec-references` spec to main, and archive the OpenSpec change
