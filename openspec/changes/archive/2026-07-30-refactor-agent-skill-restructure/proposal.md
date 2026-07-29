# Proposal: refactor-agent-skill-restructure

## Why

The agent definitions under `.opencode/agents/` mix two concerns that should be separated: **procedural knowledge** (how to review a PR, how to inspect a browser app, how to develop each subsystem) and **execution envelopes** (permissions, persona, invocation mode). Because knowledge is locked inside agent files it cannot be reused outside that agent, and the definitions have accumulated environment-specific coupling — most notably, `ci-review` hardcodes references to `.tmp/*.txt` files that only exist inside the GitHub Actions AI review job. Additionally, the developer agents' permission frontmatters still reference pre-package-split paths (`webcompy/components/*` etc.), so their edit sandboxes no longer match the actual `packages/` layout and are effectively non-functional.

## What Changes

- **Introduce 7 skills** under `.opencode/skills/` carrying the reusable knowledge, all prefixed `webcompy-`:
  - `webcompy-review` — CI review procedure, Critical Framework Invariants, review template, review perspectives. Diff/PR-context/CI-results acquisition is defined command-first (`git diff`, `gh pr diff`, `gh api`), with caller-provided files taking precedence when supplied.
  - `webcompy-inspect` — `webcompy inspect` CLI command knowledge, workflows, and file output rules.
  - `webcompy-browser-development`, `webcompy-server-development`, `webcompy-component-development`, `webcompy-docs-development` — subsystem development knowledge (responsibilities, spec references, patterns) migrated from the developer agents. Broken pre-package-split permission paths are dropped entirely.
  - `webcompy-local-ci` — local CI check procedure (from `ci-local`).
  - The tiny `runtime-analyzer` agent (17 lines) is absorbed into the browser/server development skills rather than becoming its own skill.
- **Redefine 2 agents as thin envelopes**:
  - `ci-review` → renamed **`webcompy-reviewer`**: permission frontmatter + persona + mandatory instruction to load the `webcompy-review` skill (with a Read-fallback to `SKILL.md` when the skill tool is unavailable). All `.tmp/*` file references removed from the definition.
  - `browser-inspector` → renamed **`webcompy-inspector`**: same structure, loading the `webcompy-inspect` skill.
- **Delete 6 agents**: `browser-developer`, `server-developer`, `component-developer`, `docs-developer`, `runtime-analyzer`, `ci-local`. Their knowledge lives on as skills; their (broken) permission sandboxes are not carried over.
- **Update `.github/workflows/ci.yml`** (AI Code Review job):
  - `--agent ci-review` → `--agent webcompy-reviewer`.
  - The invocation prompt keeps passing the `.tmp/*.txt` context files (that coupling now lives only in the job, not the agent). Wording updated to reference the `webcompy-review` skill instead of "agent configuration".
  - `build_digest()` `approved` branch: post full Action Items details (`ACTIONS_FULL`) instead of headings-only (`ACTIONS_HEADING`), so review findings are always machine-retrievable from PR comments.
- **Update documentation**: `AGENTS.md` (Agent Delegation Rules table becomes skill-oriented; invariant reference points to the `webcompy-review` skill), `CONTRIBUTING.md` / `CONTRIBUTING.ja.md` (`@ci-local` / `@ci-review` references).
- **Generalize one spec sentence**: `openspec/specs/async-scheduler/spec.md` currently names the `ci-review` agent as the enforcer of an invariant; reword to a tool-name-independent phrasing ("CI review"). No requirement semantics change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `async-scheduler`: the requirement "No bare asyncio scheduling shall exist outside AsyncSchedulerPort" names the `ci-review` agent as its enforcer. The sentence is generalized to a tool-name-independent phrasing ("CI review") because the agent is being renamed `webcompy-reviewer`. Requirement semantics are unchanged — only the stale tool reference is removed.

## Impact

- **Files created**: `.opencode/skills/webcompy-{review,inspect,browser-development,server-development,component-development,docs-development,local-ci}/SKILL.md`
- **Files modified**: `.github/workflows/ci.yml`, `AGENTS.md`, `CONTRIBUTING.md`, `CONTRIBUTING.ja.md`, `openspec/specs/async-scheduler/spec.md` (one sentence)
- **Files renamed/rewritten**: `.opencode/agents/ci-review.md` → `.opencode/agents/webcompy-reviewer.md`, `.opencode/agents/browser-inspector.md` → `.opencode/agents/webcompy-inspector.md`
- **Files deleted**: `.opencode/agents/{browser-developer,server-developer,component-developer,docs-developer,runtime-analyzer,ci-local}.md`
- **No impact** on framework code (`packages/`), application behavior, or public APIs.
- **Risk**: the headless `opencode run --agent webcompy-reviewer` invocation in CI must successfully load the skill; mitigated by an explicit Read-fallback instruction in the agent definition.

## Known Issues Addressed

None of the framework known issues listed in project context are affected; this change addresses tooling-level debt instead:

- Developer agent permission frontmatters reference pre-package-split paths (`webcompy/components/*`, `webcompy/cli/*`, `webcompy/testing/*`) and no longer match the `packages/` layout — resolved by removing those agents in favor of skills.
- `.tmp/*.txt` coupling between the `ci-review` agent definition and the CI job — resolved by moving file references into the job prompt only.

## Non-goals

- Any change to framework code under `packages/` or to application behavior.
- Redesigning the review output template or the CI job's diff/artifact preparation shell logic (the `.tmp/*.txt` files keep being generated exactly as today).
- Changing the review verdict semantics (`approved` / `changes_requested`) or the `REVIEW_RESULT` / `REVIEWED_AT` marker protocol.
- Introducing permission sandboxes for skills (skills cannot carry permissions; this capability is intentionally lost with the deleted developer agents).
- New spec capabilities — the only spec-level change is the `async-scheduler` wording delta above.
