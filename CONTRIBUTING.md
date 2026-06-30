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
uv run python -m pytest tests/ --tb=short                             # Unit tests
scripts/run-e2e-tests.sh                                               # E2E tests
```

See [AGENTS.md](AGENTS.md#commands-reference) for the full command reference.

---

## The Development Workflow

WebComPy uses [OpenSpec](https://github.com/fission-ai/openspec) for spec-driven
development. All non-trivial changes go through a structured lifecycle:

```
Explore → Propose → Apply → Archive
```

### Explore

Investigate problems, compare approaches, clarify requirements.

- Ask questions in [Discussions](https://github.com/kniwase/WebComPy/discussions)
- Search existing specs under `openspec/specs/`
- Review related issues and PRs
- Run `/opsx-explore` if using OpenCode

### Propose

Create a change proposal with design, specs, and tasks.

1. **Name the change**: `<type>-<short-description>` (e.g., `feat-list-reconciliation`).
   Type must be one of: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `perf`.
2. **Write artifacts** under `openspec/changes/<name>/`:
   - `proposal.md` — Motivation, scope, non-goals, known issues addressed
   - `design.md` — Technical approach and design decisions
   - `specs/` — Behavior specifications from the developer's perspective
   - `tasks.md` — Implementation tasks (each ≤2 hours)
3. **Submit as a PR** using the `openspec-proposal.md` template.
   Only OpenSpec artifacts are included — no implementation code.
4. **Review**: CI runs spec validation. The AI reviewer checks design consistency.

When creating a proposal PR, CI runs only OpenSpec validation and AI review —
lint, typecheck, and tests are skipped because no code has changed.

### Apply

Implement tasks from an approved proposal.

1. Start from the feature branch containing the proposal artifacts
2. Work through tasks in order
3. Each task should produce a meaningful commit
4. Run verification after each task

### Archive

Finalize a completed change.

1. Move artifacts from `openspec/changes/<name>/` to `openspec/changes/archive/<name>/`
2. Update main specs in `openspec/specs/` with finalized requirements
3. Submit implementation as a PR using the `default.md` template
4. After merge, archive the OpenSpec change

### Spec Writing Guidelines

- Write from the **developer's or end-user's perspective**, not the implementation's
- Use `## Purpose` to explain why and what problem it solves
- Use `## Requirements` with `### Requirement:` and `#### Scenario:` blocks
  using `WHEN/THEN/AND` format
- Describe **observable behavior**, not class hierarchies or method signatures
- Internal refactoring (no user-facing change) doesn't need a spec change

---

## Using AI Agents

### Available Agents

| Agent | Responsibility |
|---|---|
| `ci-review` | Automated pull request review against OpenSpec specs |
| `ci-local` | Runs lint, typecheck, and unit tests locally |
| `browser-developer` | Browser-side runtime (reactive, elements, router, browser API) |
| `server-developer` | Server-side code (CLI, dev server, SSG) |
| `component-developer` | UI components and docs_app |
| `docs-developer` | Documentation site under `docs_app/` |
| `browser-inspector` | Browser verification via `webcompy inspect` |

### Delegating Tasks (OpenCode)

```text
"Implement the reactive list reconciliation"
→ @browser-developer

"Update the CLI help text"
→ @server-developer

"Run CI checks before pushing"
→ @ci-local

"Review this diff against specs"
→ @ci-review
```

### How Reviews Work

Every PR is reviewed by the `ci-review` agent after CI passes. The reviewer:

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
- Reactive values defined via `Reactive`, `Computed`, `ReactiveList`, `ReactiveDict`
See [AGENTS.md](AGENTS.md#framework-invariants) for critical invariants
(dual-environment architecture, DI scope rules, reactive contracts, etc.).

### Testing

- Unit tests: `uv run python -m pytest tests/ --tb=short`
- E2E tests: `scripts/run-e2e-tests.sh`
- E2E for a single group: `scripts/run-e2e-tests.sh <group-name>`
- When adding E2E test files, update both `scripts/run-e2e-tests.sh` groups
  and `.github/workflows/ci.yml`

---

## Pull Request Process

### Choosing the Right Template

| PR contains | Template | Created by |
|---|---|---|
| Implementation code | `default.md` | AI agent (usually) |
| OpenSpec artifacts only | `openspec-proposal.md` | AI agent or human |

### Pre-Push Verification (before pushing a branch)

1. **Local CI checks** — delegate to `@ci-local` (lint, typecheck, unit tests)
2. **Code review** — delegate to `@ci-review` for spec-driven diff review

### PR Lifecycle

1. Open PR with the appropriate template
2. CI runs validation + code checks (or just OpenSpec validation for proposal PRs)
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
