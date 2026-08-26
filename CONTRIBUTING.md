# Contributing to WebComPy

## Welcome

WebComPy is a Python frontend framework that runs in the browser via PyScript.
This project assumes AI-assisted development — all contributors (human and AI agents)
collaborate through the same workflows.

**For AI agents**: Read [AGENTS.md](AGENTS.md) for the detailed technical reference
including commands, framework invariants, file-to-spec mapping, and git conventions.

---

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### Install

```bash
git clone https://github.com/kniwase/WebComPy.git
cd WebComPy
uv sync
```

The project is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
with four packages under `packages/`:
- `packages/webcompy/` — Core browser runtime (zero external deps)
- `packages/webcompy-server/` — Server-side rendering
- `packages/webcompy-cli/` — CLI tools (dev server, SSG, project init)
- `packages/webcompy-testing/` — Testing utilities

To build a wheel for an individual package (e.g., for PyScript):

```bash
uv build --package webcompy
uv build --package webcompy-server
```

Install Playwright for E2E tests (if needed):

```bash
uv sync --group dev
uv run playwright install chromium
```

### Quick Commands

```bash
uv run python -m webcompy start --dev --app docs_app.bootstrap:app     # Dev server
uv run python -m webcompy generate --app docs_app.bootstrap:app         # Static site
uv run ruff check .                                                   # Lint
uv run ruff format .                                                   # Format
uv run pyright                                                         # Type check
uv run python -m pytest tests/ --tb=short                             # Unit tests only
scripts/run-e2e-tests.sh                                               # E2E tests (core + docs, prod + static)
```

See [AGENTS.md](AGENTS.md#commands-reference) for the full command reference.

---

## The Development Workflow

WebComPy uses [OpenSpec](https://github.com/fission-ai/openspec) for spec-driven
development. All non-trivial changes go through a structured lifecycle:

```
Explore → Propose → Apply Changes → Sync Specs → Archive
```

### Explore

Investigate problems, compare approaches, clarify requirements.

- Ask questions in [Discussions](https://github.com/kniwase/WebComPy/discussions)
- Search existing specs under `openspec/specs/`
- Review related issues and PRs
- Run `/opsx-explore` if using OpenCode

### Propose

Create a change proposal with design, specs, tasks.

1. **Name the change**: `<type>-<short-description>` (e.g., `feat-list-reconciliation`).
   Type must be one of: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `perf`.
2. **Create artifacts** under `openspec/changes/<name>/` using the OpenSpec skills:
   - `openspec-new-change` to scaffold the change directory
   - `openspec-propose` to walk through artifact creation (or `openspec-ff-change`
     for a single-shot flow that fills every artifact at once)
   - `proposal.md` — Motivation, scope, non-goals, known issues addressed
   - `design.md` — Technical approach and design decisions
   - `specs/` — Behavior specifications from the developer's perspective
   - `tasks.md` — Implementation tasks (each ≤2 hours)
3. **Commit the artifacts** with `git add` and `git commit` following the
   commit message convention (`<type>: <description>`).

### Apply Changes

Implement tasks from the proposal using the `openspec-apply-change` skill.

- Work through `tasks.md` in order, producing one commit per task
- The change's status becomes `complete` when all tasks are done
- For combined PRs (proposal + implementation in one PR), Apply Changes
  happens before Sync Specs on the same branch
- For proposal-only PRs, Apply Changes starts after the proposal PR is merged

### Sync Specs

Required before submitting any implementation PR (when the change status is `complete`):

1. Run `openspec-sync-specs` to merge delta specs from `openspec/changes/<name>/specs/`
   into the main specs at `openspec/specs/<capability>/spec.md`.
2. Commit the resulting changes to `openspec/specs/` following the commit message
   convention.

Not applicable for proposal-only PRs (status remains `in-progress`).

### Archive

Required before submitting any implementation PR (when the change status is `complete`):

1. Run `openspec-archive-change` to move the change from `openspec/changes/<name>/`
   to `openspec/changes/archive/YYYY-MM-DD-<name>/`.
2. Commit the move following the commit message convention.

CI's `openspec-check` job blocks merge when a `complete` change is not archived,
so this step must complete before PR submission.

Not applicable for proposal-only PRs (status remains `in-progress`).

For PR submission mechanics, see the **Pull Request Process** section.

### Spec Writing Guidelines

- Write from the **developer's or end-user's perspective**, not the implementation's
- Use `## Purpose` to explain why and what problem it solves
- Use `## Requirements` with `### Requirement:` and `#### Scenario:` blocks
  using `WHEN/THEN/AND` format
- Describe **observable behavior**, not class hierarchies or method signatures
- Internal refactoring (no user-facing change) doesn't need a spec change

---

## Using AI Agents and Skills

OpenCode skills under `.opencode/skills/` carry reusable domain knowledge and are loaded on demand. Two thin agents exist for permission-sandboxed execution and are listed below; load a skill directly unless the agent's sandbox is required.

### Available Skills and Agents

Skills (auto-loaded by OpenCode when their description matches the task):

| Skill | Use for |
|---|---|
| `webcompy-review` | Spec-driven code review of WebComPy changes |
| `webcompy-inspect` | Browser verification via the `webcompy inspect` CLI |
| `webcompy-browser-development` | Browser-side runtime (reactive, elements, router, browser API) |
| `webcompy-server-development` | Server-side code (CLI, dev server, SSG) |
| `webcompy-component-development` | UI components and docs_app |
| `webcompy-docs-development` | Documentation site under `docs_app/` |
| `webcompy-local-ci` | Runs lint, typecheck, and unit tests locally |

Agents (provide permission sandboxes; load their companion skill):

| Agent | Responsibility |
|---|---|
| `webcompy-reviewer` | Automated pull request review against OpenSpec specs (used by CI) |
| `webcompy-inspector` | Browser verification via `webcompy inspect` (subagent-only) |

### Delegating Tasks (OpenCode)

```text
"Implement the reactive list reconciliation"
→ webcompy-browser-development skill

"Update the CLI help text"
→ webcompy-server-development skill

"Run CI checks before pushing"
→ webcompy-local-ci skill

"Review this diff against specs"
→ webcompy-review skill (or @webcompy-reviewer for sandboxed CI invocation)
```

### How Reviews Work

Every PR is reviewed by the `webcompy-reviewer` agent after CI passes. The reviewer:

1. Classifies changed files by subsystem
2. Reads corresponding OpenSpec specs
3. Checks for spec violations, logic bugs, and design issues
4. Posts a structured review in the PR

The review verdict is either `approved` or `changes_requested`.
If `changes_requested`, the PR is blocked until addressed.

Review results are visible as a PR comment with the history of all review rounds.

---

## Making Changes

### Branch Naming

```
<type>/<description>        # e.g., feat/add-di-system, fix/reactive-update-order
```

### Commit Messages

```
<type>: <description>

🤖 Generated with opencode

Co-Authored-By: opencode <noreply@opencode.ai>
```

Where `<type>` is one of: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `style`, `perf`.

The `Co-Authored-By` footer is required on every commit.

### Code Conventions

- Python 3.12+ with type annotations throughout
- Package management with `uv` — use `uv add` and `uv lock`
- No comments in code unless explicitly requested
- Component classes use `@component_template`, `@on_before_rendering`
- Reactive state primitives are specified in `openspec/specs/reactive/spec.md` and `openspec/specs/composables/spec.md`
See [AGENTS.md](AGENTS.md#framework-invariants) for critical invariants
(dual-environment architecture, DI scope rules, reactive contracts, etc.).

### Testing

Unit tests, browser tests, and E2E tests live in physically separate directories
and use distinct invocation paths:

- Unit tests: `uv run python -m pytest tests/ --tb=short` (runs only tests under `tests/`)
- Browser tests: `scripts/run-browser-tests.sh` (canonical entry point; auto-sets `WEBCOMPY_RUN_BROWSER=1`)
  - Executes `tests/browser/**` inside a real PyScript runtime in headless Chromium
  - Source-mount dev loop: `WEBCOMPY_BROWSER_SOURCE=1 scripts/run-browser-tests.sh`
  - Direct invocation (`uv run pytest tests/browser/`) fails with `pytest.UsageError`
    unless the `WEBCOMPY_RUN_BROWSER=1` environment variable is set
  - Browser tests are excluded from default discovery even when
    `WEBCOMPY_RUN_BROWSER=1` is set, unless a path argument explicitly selects
    `tests/browser/**` (a gated bare `uv run pytest` stays on the unit tier)
  - Browser test functions are plain module-level functions in pilots;
    class-based tests are technically supported via `::` qualname resolution
    but not exercised, while stacked `@pytest.mark.parametrize` marks and
    duplicate parameter values within a single mark are rejected by both the
    driver and the in-page runner (ambiguous payload dispatch)
  - Top-level imports in browser test modules must be CPython-importable;
    `import js` / `from pyscript import ...` belong inside function bodies
    and `Fake*` symbol imports from `webcompy_testing` are forbidden at top
    level (`webcompy_testing.browser_runner` is allowed as the tier API)
    (enforced by `scripts/check-browser-imports.py`)
- E2E tests: `scripts/run-e2e-tests.sh` (canonical entry point; auto-sets `WEBCOMPY_RUN_E2E=1`)
- E2E for a single group: `scripts/run-e2e-tests.sh <group-name>`
- Direct invocation of E2E tests (`uv run pytest e2e/`) fails with `pytest.UsageError`
  unless the `WEBCOMPY_RUN_E2E=1` environment variable is set.
- When adding E2E test files, update both `scripts/run-e2e-tests.sh` groups
  and `.github/workflows/ci.yml`

### Browser Dual-Run, Probes, and PyScript Version Bumps

Three extensions build on the browser test tier: the dual-run sweep
(`browser-dualrun`), the environment probe battery and version-bump sweep
(`browser-probes`), and ad-hoc in-interpreter evaluation
(`inspect-pyexec`). Their requirements live in the owning OpenSpec specs.

**Dual-run sweep** (informational) re-executes dual-run-eligible modules from
`tests/` inside the harness PyScript interpreter and diffs the outcomes with
the CPython run:

```bash
scripts/run-browser-tests.sh --dual          # writes artifacts/browser-dualrun.json
```

Eligibility is decided by a read-only AST pass in
`webcompy_cli/_browser_probes.py`. A module is ineligible when its top level
imports `js` / `pyscript` / `pyodide`, `e2e.*`, or `Fake*` symbols from
`webcompy_testing`, or when it contains module-scope side-effecting calls
(`pytest.mark.*` / `pytest.fixture(...)` call chains are allowed). Function-local
browser-only imports do not disqualify a module. A standalone comment line
overrides the judgment:

```python
# browser-dualrun: eligible   # force an ineligible module into the sweep
# browser-dualrun: skip       # keep an eligible module out of the sweep
```

The reviewed baseline lives at `tests/.dualrun/` (`eligible.txt`,
`ineligible.json`). Regenerate it after changing eligibility-relevant code or
pragmas:

```bash
python -c "from pathlib import Path; from webcompy_cli._browser_probes import classify_tests, write_baseline; write_baseline(classify_tests(Path.cwd()), Path('tests/.dualrun'))"
```

Divergence buckets are informational by default — they never fail CI.
Promote a bucket to a hard gate only after triage, via a future change.

**Environment probes** codify PyScript-runtime contracts as ordinary browser-tier
tests under `tests/browser/probes/test_probe_*.py`; the module docstring is the
human-readable contract statement. New probe files are auto-discovered by the
harness manifest with no registration. Probes are a hard gate:

```bash
scripts/run-browser-tests.sh --probes
```

Probe assertions must reflect *observed* runtime behavior: run a new probe,
then freeze the observed contract into its assertions and docstring.

**PyScript version bump procedure**:

1. Add the candidate release to `PYSCRIPT_TO_PYODIDE` in
   `packages/webcompy-cli/src/webcompy_cli/_pyodide_lock.py` (one mapping line;
   the sweep resolves candidate assets through it).
2. Run the sweep locally:
   `scripts/run-browser-version-sweep.sh <candidate>` — this executes the probe
   battery at the pinned version and at the candidate, then writes
   `artifacts/browser-version-sweep.json`. Exit code is nonzero when any probe
   regressed (passed at the pinned version but failed at the candidate).
3. Optionally dispatch the manual GitHub Actions workflow **browser-version-sweep**
   with input `pyscript_candidate_version`.
4. Only after a clean sweep, change the pin by updating `PYSCRIPT_VERSION`
   in `packages/webcompy-server/src/webcompy_server/_html.py` (plus the
   mapping entry, which step 1 already added). Candidate assets are never
   promoted automatically.

**`webcompy inspect pyexec`** evaluates ad-hoc Python inside the harness
interpreter (never on a production server process):

```bash
uv run python -m webcompy inspect pyexec "print(2+2)"        # single-shot JSON
uv run python -m webcompy inspect pyexec --file snippet.py   # evaluate a file
uv run python -m webcompy inspect pyexec --repl              # REPL over stdin lines
```

---

## Pull Request Process

### Submit

- **Template**: `.github/PULL_REQUEST_TEMPLATE.md` (the only template used for all PRs)
- **PR title and body language**: the PR title and the PR body (Description,
  Related Resources, checklist explanations, etc.) MUST be written in English
  per the Language Rules in `AGENTS.md`. AI agents that draft PRs (e.g.,
  during PR preparation steps) must produce English output regardless of the
  user's preferred chat language.
- **PR title prefix** determines CI behavior:
  - `chore:` — skips code checks (lint, typecheck, test, E2E); CI runs OpenSpec
    validation and AI review only. Suitable for proposal-only PRs.
  - `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`, `style:`, `perf:` —
    runs all checks. Suitable for implementation PRs.
- **PR shape** (proposal-only vs combined with implementation) is decided at
  PR creation time:
  - Large or contentious changes → `chore:` proposal-only PR for early review,
    then implementation PR(s) after the proposal PR merges
  - Small or self-contained changes → combined PR containing proposal artifacts
    and implementation together
- **On the proposal side of the PR Lifecycle**, CI runs only OpenSpec
  validation and AI review when the PR title starts with `chore:` — lint,
  typecheck, and tests are skipped because no code has changed.

### Pre-Push Verification (before pushing a branch)

1. **Local CI checks** — use the `webcompy-local-ci` skill (lint, typecheck, unit tests)
2. **Code review** — use the `webcompy-review` skill (or `@webcompy-reviewer` for sandboxed CI invocation)

### PR Lifecycle

1. Open PR using `.github/PULL_REQUEST_TEMPLATE.md`
2. CI runs validation + code checks (`chore:` PRs skip code checks)
3. AI review posts results as a PR comment
4. Address review feedback
5. Merge when all checks pass

### Merge Conditions

- All CI checks pass
- AI review approves (or issues are addressed)
- No completed-but-unarchived OpenSpec changes exist (enforced by CI)

---

## Issue Reporting

See [Issue Templates](.github/ISSUE_TEMPLATE/):

- **Bug report**: Use the bug report form. Specify environment (browser/server),
  versions, and reproduction steps.
- **Feature request**: Use the feature request form. Major features are expected
  to go through the OpenSpec workflow.

---

## Getting Help

- [Discussions](https://github.com/kniwase/WebComPy/discussions) — Questions, ideas, general discussion
- [Issues](https://github.com/kniwase/WebComPy/issues) — Bug reports and feature requests
- [WebComPy Docs](https://webcompy.net/) — Framework documentation and demos
