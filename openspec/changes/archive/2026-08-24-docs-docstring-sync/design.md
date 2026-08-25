## Context

See proposal.md - Why. PR-A/B added a stdlib-only presence checker, pydoclint for signature drift, and AI review for structural quality. Semantic drift (description vs. behavior) has no explicit SHALL.

## Goals / Non-Goals

**Goals:**
- Make docstring-implementation consistency a blocking requirement (same-PR update, must-fix, blocks approval).

**Non-Goals:**
- New tooling or checker changes; mechanical detection of semantic drift.

## Decisions

- **AI review owns semantic consistency** — pydoclint catches added/removed/renamed params and return/exception mismatches; stale prose and behavior mismatches require human/AI judgment. No new tool; keep checker stdlib-only.
  - Alternative: heuristic semantic diff tool — rejected (brittle, out of scope).

- **Same-PR SHALL, not eventual consistency** — reviewing diff with code+doc together is the only reliable verification point. Allowing follow-up PRs would create a window where `main` is inconsistent.

## Risks / Trade-offs

- [Reviewer misses stale prose] → Mitigated by explicit SHALL + mandatory perspective wording that blocks approval; checklist in `webcompy-review` skill.
