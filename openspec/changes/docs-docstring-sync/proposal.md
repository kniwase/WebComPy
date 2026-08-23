## Why

PR-A/B introduced 1014 docstrings and a strict checker, but the `api-docstrings` spec only requires presence and Google-style structure. Without an explicit sync rule, implementation changes can leave summaries, Args/Returns/Raises, and Attributes stale. Making same-PR docstring updates a SHALL prevents drift right after the bulk fill.

## What Changes

- Add one Requirement to `api-docstrings`: docstrings SHALL remain consistent with implementation and SHALL be updated in the same PR as the code change. Inconsistency SHALL be must-fix and SHALL block approval.
- Amend `AGENTS.md` Code Conventions (+1 line) to state the same-PR sync rule.
- Amend `.opencode/skills/webcompy-review/SKILL.md` Docstring coverage perspective to flag stale descriptions and block approval on inconsistency.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `api-docstrings`: add docstring-implementation consistency requirement and scenarios

## Impact

- Spec: `openspec/specs/api-docstrings/spec.md` delta (+1 Requirement, 2 Scenarios)
- Governance docs: `AGENTS.md`, `.opencode/skills/webcompy-review/SKILL.md` (+1 line each)
- No code, CI, or checker changes. Existing pydoclint already catches signature drift; semantic drift is newly AI-review-enforced.
