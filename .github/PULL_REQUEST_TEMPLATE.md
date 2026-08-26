<!-- All PR titles and bodies MUST be written in English. -->

<!-- For AI agents: see AGENTS.md (Language Rules) and CONTRIBUTING.md (PR Submission) for the full policy and rationale. -->

## Description

<!-- Briefly describe what this PR changes and why. -->

## Related Resources

- OpenSpec Change: `<type>-<description>` (if applicable)
- Issues: `#<n>`
- Specs affected: `openspec/specs/<name>/spec.md`

## Type of Change

<!-- Must match branch name prefix -->

- [ ] feat — New feature or enhancement
- [ ] fix — Bug fix
- [ ] refactor — Code refactoring (no behavior change)
- [ ] docs — Documentation
- [ ] chore — Maintenance, dependencies, CI
- [ ] test — Adding or updating tests
- [ ] style — Code style changes (formatting, etc.)
- [ ] perf — Performance improvement

## Breaking Changes?

- [ ] Yes (describe migration path below)
- [ ] No

## Checklist

- [ ] Change type matches branch name prefix
- [ ] PR title and body are written in English
- [ ] All completed OpenSpec changes have specs synced and are archived (if applicable)
- [ ] Tests added/updated for changed code
- [ ] Browser tests pass (if browser-runtime change) — `scripts/run-browser-tests.sh` (probes are hard gate)
- [ ] E2E tests pass (if UI-affecting change)
- [ ] Dual environment verified (browser + server)
- [ ] No new module-level globals introduced (use DI instead)
- [ ] `webcompy generate` produces correct output (if SSG-visible)
