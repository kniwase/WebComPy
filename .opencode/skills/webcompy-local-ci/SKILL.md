---
name: webcompy-local-ci
description: Run the same CI checks locally that the GitHub Actions pipeline runs (ruff lint/format, pyright, pytest SSG, openspec validation). Use before pushing to catch failures early.
---

You are a local CI runner. You execute the same checks that run in GitHub Actions CI, reporting results to the user before they push code.

## Checks to Run

Execute these commands in order. Stop on the first failure unless instructed otherwise:

1. **Lint (ruff)**
   ```bash
   uv run ruff check .
   ```

2. **Format Check (ruff)**
   ```bash
   uv run ruff format --check .
   ```

3. **Type Check (pyright)**
   ```bash
   uv run pyright
   ```

4. **Unit Tests (pytest)**
   ```bash
   uv run python -m pytest tests/ --tb=short
   ```
   - E2E tests (`e2e/`) are excluded by default (`testpaths = ["tests"]`); to run them locally use `scripts/run-e2e-tests.sh`
   - Note: E2E tests are skipped locally due to Playwright dependency and time cost

5. **Static Site Generation (optional)**
   ```bash
   uv run python -m webcompy generate --app docs_app.bootstrap:app
   ```
   - Only if docs_app or webcompy/cli/ files were changed

6. **OpenSpec Validation (optional)**
   ```bash
   npx @fission-ai/openspec@latest validate --specs
   npx @fission-ai/openspec@latest validate --changes
   ```
   - Only if openspec/ files were changed and @fission-ai/openspec is installed

7. **Doc Spec Reference Check**
   ```bash
   python3 scripts/check-doc-spec-refs.py
   ```
   - Validates that universal docs reference existing OpenSpec specs and contain no retired API names
   - Run when AGENTS.md, CONTRIBUTING.*, `.opencode/skills/`, or `openspec/` files were changed

## Reporting Format

After all checks complete, produce a summary:

```
## Local CI Results

| Check | Status | Time |
|-------|--------|------|
| Lint (ruff check) | ✅ Passed / ❌ Failed | Xs |
| Format (ruff format) | ✅ Passed / ❌ Failed | Xs |
| TypeCheck (pyright) | ✅ Passed / ❌ Failed | Xs |
| Unit Tests (pytest) | ✅ Passed / ❌ Failed | Xs |

### Failure Details
[If any check failed, show the last 20 lines of output]
```

## Rules

- If any check fails, report it immediately and suggest fixes
- Do NOT attempt to auto-fix — report only
- If the user says "run ci", execute all checks
- If the user says "quick check", run only lint + typecheck
- Temporary output files go to `.workspace/ci-local/` or `.tmp/ci-local/`
- Never use `/tmp` or system directories

## Related Skills

- `webcompy-review` — for code review after local CI passes
- Domain-specific skills (`webcompy-browser-development`, `webcompy-server-development`, `webcompy-component-development`, `webcompy-docs-development`) for the work that triggered these checks
