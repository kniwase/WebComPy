# Design: refactor-agent-skill-restructure

## Context

The repo's AI tooling layer consists of `.opencode/agents/*.md` (8 agents), `.opencode/skills/openspec-*` (10 OpenSpec workflow skills), and the AI Code Review job in `.github/workflows/ci.yml`. Two structural problems motivated this change:

1. **Knowledge is trapped in agents.** Procedural knowledge (review procedure, inspect CLI usage, subsystem development guidance) can only be consumed by the agent that hosts it. Skills are the repo's mechanism for shareable knowledge — any session can load them.
2. **Environment coupling in the wrong layer.** The `ci-review` agent references `.tmp/pr-diff.txt`, `.tmp/pr-context.txt`, `.tmp/ci-results.txt`, `.tmp/pr-diff-since-last.txt` — files that only exist because the CI job generates them. The same files are also described in the job's prompt and attached via `--file`, so the information is duplicated in two layers that can drift apart.

A third, discovered problem: the developer agents' permission frontmatters reference pre-package-split paths (`webcompy/components/*`, `webcompy/cli/*`, `webcompy/testing/*`) that no longer exist after the move to `packages/*/src/`. Their edit sandboxes are silently non-functional today.

Key constraint from the OpenCode platform: **agents and skills are not interchangeable.** Agents provide permission frontmatter, subagent context isolation, and direct invocation (`opencode run --agent <name>`, `@mention`). Skills provide on-demand knowledge injection but no permissions and no standalone invocation. The CI job can only invoke an agent, not a skill.

## Goals / Non-Goals

**Goals:**
- All reusable procedural knowledge lives in `webcompy-`-prefixed skills.
- Agents that remain are thin envelopes: permissions + persona + mandatory skill loading.
- The `ci-review` agent definition contains zero references to CI-job-generated files; that coupling lives only in the CI job prompt.
- Local (non-CI) usage of review and inspection knowledge works via skills without the CI scaffolding.
- Review comments always contain full Action Items details, regardless of verdict.

**Non-Goals:**
- Framework code changes, review template structure changes, CI job shell-logic redesign, verdict semantics changes, spec deltas.
- Recreating permission sandboxes for the deleted developer agents (skills cannot carry permissions; accepted as a trade-off).

## Decisions

### D1: Split agents into "envelope" (agent) + "knowledge" (skill)

`webcompy-reviewer` and `webcompy-inspector` keep only what only an agent can provide: permission frontmatter, persona, and an instruction to load the corresponding skill. Everything else moves to skills.

*Alternatives considered:*
- *Agent-only (status quo)*: knowledge stays non-reusable; `.tmp` coupling remains. Rejected.
- *Skill-only (delete all agents)*: CI cannot invoke a skill via `--agent`, and the review job needs `edit: deny` + `.tmp/*` allow permissions for safety. Rejected for these two agents; accepted for the developer agents (see D3).

### D2: Skill loading has an explicit Read fallback

The CI environment runs headless `opencode run --agent webcompy-reviewer`. Whether the `skill` tool is available in that mode is an unverified assumption. Both envelope agents therefore instruct: "Load the `<skill>` skill. If the skill tool is unavailable, Read `.opencode/skills/<skill>/SKILL.md` directly." The fallback is behaviorally equivalent because a skill's content is just its `SKILL.md`.

*Alternatives considered:*
- *Inline the full procedure in the agent as a fallback*: reintroduces duplication. Rejected.
- *Verify skill availability in CI first, no fallback*: a failure mode that blocks all reviews if the assumption breaks. Rejected.

### D3: Developer agents are deleted, not converted to thin envelopes

The six non-review/inspection agents (`browser-developer`, `server-developer`, `component-developer`, `docs-developer`, `runtime-analyzer`, `ci-local`) provided three things: knowledge (→ skills), handoff rules (→ replaced by skill `description` fields, which OpenCode uses for automatic skill matching), and permission sandboxes (→ already broken due to stale paths; not recreated). `runtime-analyzer` (17 lines) is absorbed into the browser/server development skills rather than standing alone.

*Alternatives considered:*
- *Fix permission paths and keep agents*: preserves subagent context isolation, but the maintainer judged the delegation layer unnecessary; AGENTS.md's File→Spec mapping already carries the routing knowledge. Rejected.
- *One merged `webcompy-development` skill*: fewer files, but domain routing via skill descriptions works better with focused skills. Rejected.

### D4: Diff/context acquisition is command-first, file-override

`webcompy-review` defines acquisition of the PR diff, PR context, and CI results via commands (`git diff <base>...HEAD`, `gh pr diff`, `gh api`) as the default path, with an explicit rule: when the caller provides file paths (as the CI job does with `.tmp/*.txt`), those files take precedence and commands are not re-run. This keeps the skill self-sufficient for local use while letting CI inject its prepared artifacts (including the incremental-diff logic that requires the `REVIEWED_AT` marker lookup — that logic stays in the job's shell where the GitHub API context lives).

### D5: Review template and invariants move together into `webcompy-review`

The review output template is a contract with `ci.yml`'s awk-based section extraction (`extract()` / `extract_bullets()`). The Critical Framework Invariants are the review's domain checklist. Both are knowledge, not envelope, so both move to the skill. `AGENTS.md` keeps its short invariant summary but its "complete invariant reference" pointer changes to the skill. Section names in the template MUST NOT change (CI extraction depends on them).

### D6: Approved reviews post full Action Items

`build_digest()` in `ci.yml` currently uses `ACTIONS_HEADING` (bullet headings only) for `approved` and `ACTIONS_FULL` (details) for `changes_requested`. Change: use `ACTIONS_FULL` in both branches so AI agents reading PR comments can always retrieve full findings. Trade-off: longer approved comments — accepted.

### D7: Naming

All skills take the `webcompy-` prefix (groups project skills apart from `openspec-*` and any global skills). Remaining agents are renamed to match: `webcompy-reviewer` (loads `webcompy-review`), `webcompy-inspector` (loads `webcompy-inspect`). Lowercase kebab-case per OpenCode convention. Development skills use full words: `webcompy-browser-development`, `webcompy-server-development`, `webcompy-component-development`, `webcompy-docs-development`, plus `webcompy-local-ci`.

### D8: `async-scheduler` spec sentence is generalized via a delta

`openspec/specs/async-scheduler/spec.md` names the `ci-review` agent as the enforcer of the "No bare asyncio scheduling" requirement. The sentence is reworded to a tool-name-independent phrase ("CI review") through a `MODIFIED Requirements` delta in this change (the full requirement block is copied and only that sentence changes), following the repo's OpenSpec discipline of never editing main specs directly. Requirement semantics are unchanged, and the spec becomes robust against future tool renames.

## Risks / Trade-offs

- [Skill tool unavailable or behaves differently in headless `opencode run`] → D2's Read fallback makes the envelope self-sufficient either way; additionally, the CI job prompt continues to state the critical output contract (write `.tmp/review-output.md`, `REVIEW_RESULT` marker) so a total skill-loading failure degrades rather than breaks.
- [Knowledge drifts between skill and AGENTS.md summary] → AGENTS.md keeps only a pointer plus its existing short list; the skill is declared the single complete reference (updating AGENTS.md maintenance rules accordingly).
- [Losing permission sandboxes increases blast radius of subagent mistakes] → accepted; the deleted sandboxes were already non-functional (stale paths), and the high-risk operations (review, inspection) retain sandboxes via the two remaining agents.
- [Renaming breaks external references] → repo-wide references (`ci.yml`, `AGENTS.md`, `CONTRIBUTING*.md`, `async-scheduler` spec) are all updated in this change; archived change docs under `openspec/changes/archive/` are intentionally left as historical record.
- [Longer approved comments] → accepted per D6.

## Migration Plan

Single PR, no runtime deployment. Order: create skills → rewrite/rename agents → delete old agents → update `ci.yml` → update docs and the one spec sentence. Rollback is `git revert` of the PR. The first AI review run after merge should be watched to confirm the skill loads (or the fallback engages) in the headless environment.

## Open Questions

None blocking. Verification item (not a decision): confirm skill loading works in the headless CI environment on the first post-merge review run.
