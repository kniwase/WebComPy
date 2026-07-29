# Tasks: refactor-agent-skill-restructure

## 1. Skills: review & inspection

- [x] 1.1 Create `.opencode/skills/webcompy-review/SKILL.md`: frontmatter (name, description) + Review Procedure with command-first acquisition (`git diff`, `gh pr diff`, `gh api`) and caller-provided-file precedence + Critical Framework Invariants (migrated verbatim from `.opencode/agents/ci-review.md`) + General Review Perspectives + review output template (section names unchanged — CI awk extraction contract)
- [x] 1.2 Create `.opencode/skills/webcompy-inspect/SKILL.md`: inspect CLI subcommands (serve/stop/screenshot/console/query/click/navigate/verify), typical workflows, file output rules, image analysis notes (migrated from `browser-inspector.md`)

## 2. Skills: development domains

- [x] 2.1 Create `.opencode/skills/webcompy-browser-development/SKILL.md`: responsibilities, spec references, patterns from `browser-developer.md` (drop stale permission paths); absorb runtime-context analysis guidance from `runtime-analyzer.md`
- [x] 2.2 Create `.opencode/skills/webcompy-server-development/SKILL.md`: responsibilities, spec references, patterns from `server-developer.md` (drop stale permission paths); absorb runtime-context analysis guidance
- [x] 2.3 Create `.opencode/skills/webcompy-component-development/SKILL.md`: scope, boundaries, patterns from `component-developer.md`
- [x] 2.4 Create `.opencode/skills/webcompy-docs-development/SKILL.md`: docs_app rules from `docs-developer.md`
- [x] 2.5 Create `.opencode/skills/webcompy-local-ci/SKILL.md`: check sequence, reporting format, rules from `ci-local.md`
- [x] 2.6 Write skill `description` fields so OpenCode's automatic skill matching replaces the old agent handoff rules (each description states when the skill applies)

## 3. Agents: redefine envelopes

> File deletions in this section (8 files) are pre-authorized by the user.

- [x] 3.1 Rewrite `.opencode/agents/ci-review.md` → `.opencode/agents/webcompy-reviewer.md`: keep permission frontmatter and persona; remove all `.tmp/*.txt` references and procedural content; add mandatory `webcompy-review` skill loading with Read-fallback to `SKILL.md`; delete old `ci-review.md`
- [x] 3.2 Rewrite `.opencode/agents/browser-inspector.md` → `.opencode/agents/webcompy-inspector.md`: keep permission frontmatter and persona; remove procedural content; add mandatory `webcompy-inspect` skill loading with Read-fallback; replace "delegate to browser-developer" coordination note; delete old `browser-inspector.md`
- [x] 3.3 Delete `.opencode/agents/browser-developer.md`, `server-developer.md`, `component-developer.md`, `docs-developer.md`, `runtime-analyzer.md`, `ci-local.md`

## 4. CI workflow

- [ ] 4.1 Update `.github/workflows/ci.yml`: `--agent ci-review` → `--agent webcompy-reviewer`; update prompt wording ("your agent configuration" → "the webcompy-review skill")
- [ ] 4.2 Update `build_digest()` approved branch: use `ACTIONS_FULL` instead of `ACTIONS_HEADING` so Action Items details are always posted
- [ ] 4.3 Verify the awk `extract()` / `extract_bullets()` logic still matches the (unchanged) template section names

## 5. Documentation & spec wording

- [ ] 5.1 Update `AGENTS.md`: replace the Agent Delegation Rules table with skill-oriented guidance; point the "complete invariant reference" to the `webcompy-review` skill; remove references to deleted agents
- [ ] 5.2 Update `CONTRIBUTING.md` and `CONTRIBUTING.ja.md`: replace `@ci-local` / `@ci-review` mentions with the new skill/agent names
- [ ] 5.3 Confirm no other live doc references the old agent names (archived changes under `openspec/changes/archive/` are intentionally untouched)

## 6. Verification

- [ ] 6.1 Run `openspec validate refactor-agent-skill-restructure` and confirm the change is valid
- [ ] 6.2 Static verification: confirm all 7 skills exist with required frontmatter (`name:` matching directory, `description:` present and meaningful); confirm both redefined agents contain the mandatory skill-load instruction with Read-fallback; confirm `ci.yml` uses `--agent webcompy-reviewer` and posts full Action Items; confirm the leftover-name grep returns 0 hits in live files (excluding `openspec/changes/archive/` and the current change's proposal/design/tasks)
- [ ] 6.3 After merge, watch the first AI Code Review job run to confirm skill loading (or Read-fallback) works in the headless environment and the review comment posts with full Action Items
